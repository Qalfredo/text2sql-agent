from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
import yaml
from smolagents import CodeAgent, tool
from smolagents.agents import RunResult

from .config import Settings
from .database import SQLDatabaseClient, SQLGuardError, build_schema_context
from .docs_loader import load_documentation_bundle


def _build_ollama_tags_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[: -len("/v1")]
    tags_path = f"{path}/api/tags" if path else "/api/tags"
    return parsed._replace(path=tags_path, params="", query="", fragment="").geturl()


def _validate_ollama_runtime(settings: Settings) -> None:
    assert settings.ollama_base_url is not None

    tags_url = _build_ollama_tags_url(settings.ollama_base_url)
    try:
        response = requests.get(tags_url, timeout=5)
        response.raise_for_status()
    except requests.Timeout as exc:
        raise ValueError(
            "Ollama startup check timed out while contacting "
            f"{tags_url} for model '{settings.model_id}'. "
            "Make sure `ollama serve` is running locally, then retry. "
            f"If the model has not been pulled yet, run `ollama pull {settings.model_id}`."
        ) from exc
    except requests.ConnectionError as exc:
        raise ValueError(
            "Ollama startup check could not connect to the local Ollama server. "
            f"Expected {settings.ollama_base_url} for model '{settings.model_id}'. "
            "Start Ollama with `ollama serve` and ensure the API is reachable. "
            f"If needed, pull the model first with `ollama pull {settings.model_id}`."
        ) from exc
    except requests.RequestException as exc:
        raise ValueError(
            "Ollama startup check failed. Expected a local Ollama server at "
            f"{settings.ollama_base_url} for model '{settings.model_id}'. "
            "Make sure Ollama is installed, run `ollama serve`, and pull the model with "
            f"`ollama pull {settings.model_id}`."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(
            "Ollama startup check failed because the server response was not valid JSON. "
            f"Expected an Ollama API endpoint at {settings.ollama_base_url}."
        ) from exc
    models = payload.get("models", [])
    model_names = {
        str(item.get("model") or item.get("name") or "").strip()
        for item in models
        if str(item.get("model") or item.get("name") or "").strip()
    }
    if settings.model_id not in model_names:
        available = ", ".join(sorted(model_names)) if model_names else "none returned by Ollama"
        raise ValueError(
            "Ollama server is reachable but the configured model is not available. "
            f"Expected '{settings.model_id}' at {settings.ollama_base_url}. "
            f"Available models: {available}. "
            f"Run `ollama pull {settings.model_id}` and retry."
        )


def _build_model(settings: Settings):
    provider = settings.model_provider

    if provider == "openai":
        from smolagents.models import OpenAIServerModel

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when MODEL_PROVIDER=openai")

        model_kwargs = {
            "model_id": settings.model_id,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            model_kwargs["api_base"] = settings.openai_base_url
        return OpenAIServerModel(**model_kwargs)

    if provider == "huggingface":
        if not settings.hf_token:
            raise ValueError("HF_TOKEN is required when MODEL_PROVIDER=huggingface")

        # Smolagents versions expose either HfApiModel or InferenceClientModel.
        try:
            from smolagents.models import HfApiModel

            return HfApiModel(model_id=settings.model_id, token=settings.hf_token)
        except ImportError:
            from smolagents.models import InferenceClientModel

            return InferenceClientModel(model_id=settings.model_id, token=settings.hf_token)

    if provider == "google":
        from smolagents.models import LiteLLMModel

        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when MODEL_PROVIDER=google")

        model_kwargs = {
            "model_id": settings.model_id,
            "api_key": settings.google_api_key,
        }
        if settings.google_api_base:
            model_kwargs["api_base"] = settings.google_api_base
        return LiteLLMModel(**model_kwargs)

    if provider == "ollama":
        from smolagents.models import OpenAIServerModel

        _validate_ollama_runtime(settings)
        return OpenAIServerModel(
            model_id=settings.model_id,
            api_base=settings.ollama_base_url,
            api_key="ollama",
        )

    raise ValueError("MODEL_PROVIDER must be one of: openai, huggingface, ollama, google.")


@dataclass
class AgentRuntime:
    agent: CodeAgent
    database_client: SQLDatabaseClient

    def run(self, question: str) -> str:
        return str(self.agent.run(question))

    def run_full(self, question: str) -> RunResult:
        result = self.agent.run(question, return_full_result=True)
        assert isinstance(result, RunResult)
        return result


def build_agent_runtime(settings: Settings) -> AgentRuntime:
    database_client = SQLDatabaseClient(
        url=settings.database_url,
        allowed_tables=settings.allowed_tables,
        sql_dialect=settings.sql_dialect,
        max_rows=settings.max_rows,
    )

    schema_map = database_client.fetch_schema()
    docs_bundle = load_documentation_bundle(settings)
    schema_context = build_schema_context(
        schema_map=schema_map,
        column_docs=docs_bundle.column_docs,
        context_docs=docs_bundle.context_docs,
        database_label=settings.database_label,
    )

    @tool
    def query_database(sql_query: str) -> str:
        """
        Execute a read-only SQL query against the configured database.

        Args:
            sql_query: A single SELECT query.
        """
        try:
            headers, rows = database_client.execute_query(sql_query)
        except SQLGuardError as exc:
            return f"Query blocked by policy: {exc}"
        except Exception as exc:  # noqa: BLE001
            return f"Query failed: {exc}"

        if not rows:
            return "Query succeeded with 0 rows."

        display_limit = 20
        display_rows = rows[:display_limit]
        lines = [" | ".join(headers), " | ".join(["---"] * len(headers))]
        for row in display_rows:
            lines.append(" | ".join(str(value) for value in row))
        lines.append(f"\nShowing {len(display_rows)} of {len(rows)} row(s).")
        if len(rows) > display_limit:
            lines.append(
                f"Note: this result set is too large to display in full. "
                f"Only the first {display_limit} rows are shown. "
                "Consider refining your query with filters or aggregations to get a more specific result."
            )
        return "\n".join(lines)

    query_database.description = (
        f"Use this tool for SQL retrieval from the configured {settings.database_label}. "
        "You must only query allowlisted tables. "
        "Schema documentation:\n"
        f"{schema_context}"
    )

    model = _build_model(settings)

    prompt_templates = yaml.safe_load(
        importlib.resources.files("smolagents.prompts").joinpath("code_agent.yaml").read_text()
    )
    prompt_templates["system_prompt"] += (
        "\n\nYou are a careful text-to-SQL assistant. "
        "Always call query_database to get data before answering factual questions. "
        "If the tool returns a policy block, explain how to rephrase within allowed tables.\n\n"
        "IMPORTANT rules for using query_database:\n"
        "1. query_database always returns a plain string (a markdown table). "
        "Never treat the result as a list or dict. Never use .get(), indexing, or iteration on it.\n"
        "2. Do ALL filtering, joining, aggregation, and sorting inside the SQL query itself. "
        "Never try to process query results in Python.\n"
        "3. Write a single SQL query that returns the final answer directly. "
        "Then call final_answer() with that string result.\n"
        "4. When joining Artist and Album, always join Artist explicitly: "
        "JOIN Artist ar ON al.ArtistId = ar.ArtistId — Album has no Name column for the artist.\n"
        "5. Column names are case-sensitive in SQLite. Use exact names from the schema."
    )

    agent = CodeAgent(
        tools=[query_database],
        model=model,
        add_base_tools=False,
        max_steps=6,
        prompt_templates=prompt_templates,
    )

    return AgentRuntime(agent=agent, database_client=database_client)
