from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sql_agent.schema_markdown import export_schema_markdown


def _discover_source_sqlite(explicit_repo_dir: str | None) -> Path:
    candidates: list[Path] = []
    if explicit_repo_dir:
        candidates.append(Path(explicit_repo_dir).expanduser().resolve())

    project_root = Path(__file__).resolve().parents[1]
    candidates.extend(
        [
            project_root.parent / "chinook-database",
            project_root / "vendor" / "chinook-database",
        ]
    )

    for candidate in candidates:
        sqlite_path = candidate / "ChinookDatabase" / "DataSources" / "Chinook_Sqlite.sqlite"
        if sqlite_path.exists():
            return sqlite_path

    raise FileNotFoundError(
        "Could not find Chinook_Sqlite.sqlite. Pass --chinook-repo-dir pointing to a clone of "
        "https://github.com/lerocha/chinook-database.git"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up the Chinook SQLite example and export Markdown docs.")
    parser.add_argument("--chinook-repo-dir", default=None)
    parser.add_argument("--output-root", default="examples/chinook")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    output_root = (project_root / args.output_root).resolve()
    data_dir = output_root / "data"
    docs_dir = output_root / "docs" / "markdown"
    data_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    source_sqlite = _discover_source_sqlite(args.chinook_repo_dir)
    target_sqlite = data_dir / "chinook.sqlite"
    shutil.copy2(source_sqlite, target_sqlite)

    database_url = f"sqlite:///{target_sqlite}"
    export_result = export_schema_markdown(
        database_url=database_url,
        output_dir=str(docs_dir),
        database_label="Chinook SQLite database",
    )

    env_path = output_root / ".env.generated"
    env_path.write_text(
        "\n".join(
            [
                f"APP_DATABASE_URL={database_url}",
                "DATABASE_LABEL=Chinook SQLite database",
                "SQL_DIALECT=sqlite",
                f"MARKDOWN_DOCS_DIR={docs_dir}",
                f"ALLOWED_TABLES={','.join(export_result.table_refs)}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Copied SQLite database to {target_sqlite}")
    print(f"Generated Markdown docs in {docs_dir}")
    print(f"Wrote environment snippet to {env_path}")


if __name__ == "__main__":
    main()
