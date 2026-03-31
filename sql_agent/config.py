import os
from dataclasses import dataclass
from urllib.parse import quote_plus, urlencode


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _get_env(primary: str, legacy: str, default: str = "") -> str:
    return os.getenv(primary, os.getenv(legacy, default)).strip()


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
    openai_api_key: str | None
    openai_base_url: str | None
    hf_token: str | None


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

    return Settings(
        database_url=database_url,
        allowed_tables=allowed_tables,
        max_rows=int(os.getenv("MAX_RESULT_ROWS", "200")),
        markdown_docs_dir=os.getenv("MARKDOWN_DOCS_DIR", "docs/markdown").strip() or None,
        sql_dialect=os.getenv("SQL_DIALECT", "postgres").strip(),
        database_label=os.getenv("DATABASE_LABEL", "SQL database").strip(),
        model_provider=os.getenv("MODEL_PROVIDER", "openai").strip().lower(),
        model_id=os.getenv("MODEL_ID", "gpt-4o-mini").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        hf_token=os.getenv("HF_TOKEN"),
    )
