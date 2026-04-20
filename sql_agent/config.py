import os
from dataclasses import dataclass
from urllib.parse import quote_plus, urlencode, urlparse


SUPPORTED_MODEL_PROVIDERS = {"openai", "huggingface", "ollama", "google"}
OLLAMA_MODEL_ALIASES = {
    "gemma4:2b": "gemma4:e2b",
    "gemma4:4b": "gemma4:e4b",
}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _get_env(primary: str, legacy: str, default: str = "") -> str:
    return os.getenv(primary, os.getenv(legacy, default)).strip()


def _default_model_id(provider: str) -> str:
    if provider == "ollama":
        return "gemma4:e2b"
    if provider == "google":
        return "gemini/gemini-2.5-flash-lite"
    return "gpt-4o-mini"


def _normalize_model_id(provider: str, model_id: str) -> str:
    cleaned = model_id.strip()
    if provider == "ollama":
        return OLLAMA_MODEL_ALIASES.get(cleaned, cleaned)
    return cleaned


def _validate_http_url(name: str, value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name} must be a valid http(s) URL.")
    return value.rstrip("/")


def _build_database_url_from_env() -> str:
    host = _get_env("DATABASE_HOST", "REDSHIFT_HOST")
    port = _get_env("DATABASE_PORT", "REDSHIFT_PORT", "5439")
    user = _get_env("DATABASE_USER", "REDSHIFT_USER")
    password = _get_env("DATABASE_PASSWORD", "REDSHIFT_PASSWORD")
    database = _get_env("DATABASE_NAME", "REDSHIFT_DATABASE")
    prod_database = _get_env("DATABASE_PROD_NAME", "REDSHIFT_PROD_DATABASE")
    dev_database = _get_env("DATABASE_DEV_NAME", "REDSHIFT_DEV_DATABASE")
    sqlalchemy_scheme = _get_env(
        "DATABASE_SQLALCHEMY_SCHEME",
        "REDSHIFT_SQLALCHEMY_SCHEME",
        "postgresql+psycopg2",
    )
    sslmode = _get_env("DATABASE_SSLMODE", "REDSHIFT_SSLMODE", "require")
    sslrootcert = _get_env("DATABASE_SSLROOTCERT", "REDSHIFT_SSLROOTCERT")

    if not database:
        database = dev_database or prod_database

    if not (host and user and password and database):
        return ""

    query_params: dict[str, str] = {}
    if sslmode:
        query_params["sslmode"] = sslmode
    if sslrootcert:
        query_params["sslrootcert"] = sslrootcert
    query_string = f"?{urlencode(query_params)}" if query_params else ""

    return (
        f"{sqlalchemy_scheme}://{quote_plus(user)}:{quote_plus(password)}@"
        f"{host}:{port}/{database}{query_string}"
    )


@dataclass
class Settings:
    database_url: str
    allowed_tables: list[str]
    max_rows: int
    markdown_docs_dir: str | None
    sql_dialect: str
    database_label: str
    model_provider: str
    model_id: str
    ollama_base_url: str | None
    openai_api_key: str | None
    openai_base_url: str | None
    hf_token: str | None
    google_api_key: str | None
    google_api_base: str | None


def load_settings() -> Settings:
    database_url = os.getenv("APP_DATABASE_URL", os.getenv("DATABASE_URL", os.getenv("REDSHIFT_URL", ""))).strip()
    if not database_url:
        database_url = _build_database_url_from_env()
    allowed_tables = _split_csv(os.getenv("ALLOWED_TABLES", ""))

    if not database_url:
        raise ValueError(
            "Set APP_DATABASE_URL (or legacy DATABASE_URL) or provide DATABASE_HOST, DATABASE_USER, "
            "DATABASE_PASSWORD, and DATABASE_NAME (legacy REDSHIFT_* variables are still supported)."
        )
    if not allowed_tables:
        raise ValueError("ALLOWED_TABLES is required (comma-separated table names or schema.table names).")

    model_provider = os.getenv("MODEL_PROVIDER", "openai").strip().lower()
    if model_provider not in SUPPORTED_MODEL_PROVIDERS:
        raise ValueError(
            "MODEL_PROVIDER must be one of: openai, huggingface, ollama, google."
        )

    model_id = _normalize_model_id(
        model_provider,
        os.getenv("MODEL_ID", "").strip() or _default_model_id(model_provider),
    )
    ollama_base_url: str | None = None
    if model_provider == "ollama" or os.getenv("OLLAMA_BASE_URL", "").strip():
        ollama_base_url_raw = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip()
        ollama_base_url = _validate_http_url("OLLAMA_BASE_URL", ollama_base_url_raw)

    return Settings(
        database_url=database_url,
        allowed_tables=allowed_tables,
        max_rows=int(os.getenv("MAX_RESULT_ROWS", "200")),
        markdown_docs_dir=os.getenv("MARKDOWN_DOCS_DIR", "docs/markdown").strip() or None,
        sql_dialect=os.getenv("SQL_DIALECT", "postgres").strip(),
        database_label=os.getenv("DATABASE_LABEL", "SQL database").strip(),
        model_provider=model_provider,
        model_id=model_id,
        ollama_base_url=ollama_base_url,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        hf_token=os.getenv("HF_TOKEN"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        google_api_base=os.getenv("GOOGLE_API_BASE"),
    )
