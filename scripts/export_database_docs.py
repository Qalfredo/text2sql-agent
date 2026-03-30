from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sql_agent.schema_markdown import export_schema_markdown


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export database schema documentation to Markdown files.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "").strip())
    parser.add_argument("--output-dir", default="docs/markdown")
    parser.add_argument("--database-label", default=os.getenv("DATABASE_LABEL", "SQL database").strip())
    parser.add_argument("--allowed-tables", default=os.getenv("ALLOWED_TABLES", "").strip())
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("Provide --database-url or set DATABASE_URL.")

    result = export_schema_markdown(
        database_url=args.database_url,
        output_dir=args.output_dir,
        database_label=args.database_label,
        allowed_tables=_split_csv(args.allowed_tables),
    )

    print(f"Wrote {len(result.files_written)} file(s) to {Path(args.output_dir).resolve()}")
    print("Allowed tables:")
    print(",".join(result.table_refs))


if __name__ == "__main__":
    main()
