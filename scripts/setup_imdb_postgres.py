from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sql_agent.schema_markdown import export_schema_markdown


DEFAULT_ALLOWED_TABLES = [
    "imdb_core.title_genre",
    "imdb_core.title_director",
    "imdb_core.title_writer",
    "imdb_core.name_known_for_title",
    "imdb_core.name_primary_profession",
    "imdb_raw.title_basics",
    "imdb_raw.name_basics",
    "imdb_raw.title_ratings",
    "imdb_raw.title_principals",
    "imdb_raw.title_episode",
]
DEFAULT_IMDB_DATABASE_URL = "postgresql+psycopg2://alfredo@localhost:5432/imdb"


def _discover_imdb_repo(explicit_repo_dir: str | None) -> Path:
    candidates: list[Path] = []
    if explicit_repo_dir:
        candidates.append(Path(explicit_repo_dir).expanduser().resolve())

    project_root = Path(__file__).resolve().parents[1]
    candidates.extend(
        [
            project_root.parent / "imdb-postgres-dataset",
            project_root / "vendor" / "imdb-postgres-dataset",
        ]
    )

    for candidate in candidates:
        if (candidate / "README.md").exists() and (candidate / "scripts" / "bootstrap.py").exists():
            return candidate

    raise FileNotFoundError(
        "Could not find the sibling imdb-postgres-dataset repo. Pass --imdb-repo-dir pointing to that repo."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up the IMDb Postgres example and export Markdown docs.")
    parser.add_argument("--imdb-repo-dir", default=None)
    parser.add_argument("--database-url", default=os.getenv("APP_DATABASE_URL", "").strip())
    parser.add_argument("--output-root", default="examples/imdb")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    output_root = (project_root / args.output_root).resolve()
    docs_dir = output_root / "docs" / "markdown"
    docs_dir.mkdir(parents=True, exist_ok=True)

    imdb_repo_dir = _discover_imdb_repo(args.imdb_repo_dir)
    database_url = args.database_url or DEFAULT_IMDB_DATABASE_URL

    export_result = export_schema_markdown(
        database_url=database_url,
        output_dir=str(docs_dir),
        database_label="IMDb Postgres database",
        allowed_tables=DEFAULT_ALLOWED_TABLES,
    )

    env_lines = [
        f"APP_DATABASE_URL={database_url}",
        "DATABASE_LABEL=IMDb Postgres database",
        "SQL_DIALECT=postgres",
        f"MARKDOWN_DOCS_DIR={docs_dir}",
        f"ALLOWED_TABLES={','.join(export_result.table_refs)}",
        "",
        f"# Companion repo: {imdb_repo_dir}",
        "# IMDb datasets are non-commercial and governed by IMDb's official terms:",
        "# https://developer.imdb.com/non-commercial-datasets/",
        "# https://datasets.imdbws.com/",
        "",
    ]

    env_path = output_root / ".env.generated"
    env_path.write_text("\n".join(env_lines), encoding="utf-8")

    gemma_env_path = output_root / ".env.gemma4"
    gemma_env_path.write_text(
        "\n".join(
            env_lines
            + [
                "MODEL_PROVIDER=ollama",
                "MODEL_ID=gemma4:e2b",
                "OLLAMA_BASE_URL=http://localhost:11434/v1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Using companion repo: {imdb_repo_dir}")
    print(f"Generated Markdown docs in {docs_dir}")
    print(f"Allowlisted tables: {','.join(export_result.table_refs)}")
    print(f"Wrote environment snippet to {env_path}")
    print(f"Wrote Gemma 4 Ollama snippet to {gemma_env_path}")


if __name__ == "__main__":
    main()
