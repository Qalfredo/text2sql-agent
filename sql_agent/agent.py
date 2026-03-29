from __future__ import annotations

import importlib.resources
from dataclasses import dataclass

import yaml
from smolagents import CodeAgent, tool

from .config import Settings
from .database import SQLDatabaseClient, SQLGuardError, build_schema_context
from .docs_loader import load_documentation_bundle


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

    raise ValueError("MODEL_PROVIDER must be either 'openai' or 'huggingface'.")


@dataclass
class AgentRuntime:
    agent: CodeAgent
    database_client: SQLDatabaseClient

    def run(self, question: str) -> str:
        return str(self.agent.run(question))


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

        preview_rows = rows[: settings.max_rows]
        lines = [" | ".join(headers), " | ".join(["---"] * len(headers))]
        for row in preview_rows:
            lines.append(" | ".join(str(value) for value in row))
        lines.append(f"\nReturned {len(preview_rows)} row(s) (max {settings.max_rows}).")
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
        "If the tool returns a policy block, explain how to rephrase within allowed tables."
    )

    agent = CodeAgent(
        tools=[query_database],
        model=model,
        add_base_tools=False,
        max_steps=6,
        prompt_templates=prompt_templates,
    )

    return AgentRuntime(agent=agent, database_client=database_client)
