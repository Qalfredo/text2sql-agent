from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SYSTEM_SCHEMAS = {"information_schema", "pg_catalog", "pg_toast", "sys"}


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool
    default: str | None
    is_primary_key: bool


@dataclass(frozen=True)
class ForeignKeyInfo:
    constrained_columns: list[str]
    referred_table: str
    referred_schema: str | None
    referred_columns: list[str]


@dataclass(frozen=True)
class IndexInfo:
    name: str
    columns: list[str]
    unique: bool


@dataclass(frozen=True)
class TableSchemaDoc:
    schema_name: str | None
    table_name: str
    columns: list[ColumnInfo]
    foreign_keys: list[ForeignKeyInfo]
    indexes: list[IndexInfo]

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}" if self.schema_name else self.table_name


@dataclass(frozen=True)
class ExportResult:
    table_refs: list[str]
    files_written: list[str]


def _join_table_ref(schema_name: str | None, table_name: str) -> str:
    return f"{schema_name}.{table_name}" if schema_name else table_name


def _split_table_ref(table_ref: str) -> tuple[str | None, str]:
    if "." not in table_ref:
        return None, table_ref
    schema_name, table_name = table_ref.split(".", 1)
    return schema_name, table_name


def _slugify_table_ref(table_ref: str) -> str:
    return table_ref.lower().replace(".", "__").replace(" ", "_")


def _render_table_doc(table_doc: TableSchemaDoc) -> str:
    lines = [
        f"# Table: {table_doc.qualified_name}",
        "",
        "## Summary",
        "",
        f"- Column count: {len(table_doc.columns)}",
        f"- Primary key columns: {', '.join(col.name for col in table_doc.columns if col.is_primary_key) or 'None'}",
    ]

    lines.extend(
        [
            "",
            "## Columns",
            "",
            "| Column | Type | Nullable | Default | Primary Key |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for column in table_doc.columns:
        lines.append(
            f"| {column.name} | {column.data_type} | "
            f"{'Yes' if column.nullable else 'No'} | {column.default or ''} | "
            f"{'Yes' if column.is_primary_key else 'No'} |"
        )

    lines.extend(["", "## Foreign Keys", ""])
    if table_doc.foreign_keys:
        lines.extend(
            [
                "| Columns | References | Referenced Columns |",
                "| --- | --- | --- |",
            ]
        )
        for foreign_key in table_doc.foreign_keys:
            reference = _join_table_ref(foreign_key.referred_schema, foreign_key.referred_table)
            lines.append(
                f"| {', '.join(foreign_key.constrained_columns)} | {reference} | "
                f"{', '.join(foreign_key.referred_columns)} |"
            )
    else:
        lines.append("No foreign keys found.")

    lines.extend(["", "## Indexes", ""])
    if table_doc.indexes:
        lines.extend(
            [
                "| Index | Columns | Unique |",
                "| --- | --- | --- |",
            ]
        )
        for index in table_doc.indexes:
            lines.append(f"| {index.name} | {', '.join(index.columns) or '(expression)'} | {'Yes' if index.unique else 'No'} |")
    else:
        lines.append("No indexes found.")

    return "\n".join(lines) + "\n"


def _render_overview(database_label: str, table_docs: list[TableSchemaDoc]) -> str:
    lines = [
        f"# {database_label} schema overview",
        "",
        f"- Table count: {len(table_docs)}",
        "",
        "## Tables",
        "",
        "| Table | Columns | Foreign Keys | Indexes |",
        "| --- | --- | --- | --- |",
    ]
    for table_doc in table_docs:
        lines.append(
            f"| {table_doc.qualified_name} | {len(table_doc.columns)} | "
            f"{len(table_doc.foreign_keys)} | {len(table_doc.indexes)} |"
        )
    return "\n".join(lines) + "\n"


def _write_markdown_docs(output_dir: str, database_label: str, table_docs: list[TableSchemaDoc]) -> ExportResult:
    root = Path(output_dir).expanduser().resolve()
    tables_dir = root / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    files_written: list[str] = []

    overview_path = root / "schema_overview.md"
    overview_path.write_text(_render_overview(database_label, table_docs), encoding="utf-8")
    files_written.append(str(overview_path))

    allowed_tables_path = root / "allowed_tables.txt"
    allowed_tables = [_join_table_ref(doc.schema_name, doc.table_name) for doc in table_docs]
    allowed_tables_path.write_text(",".join(allowed_tables) + "\n", encoding="utf-8")
    files_written.append(str(allowed_tables_path))

    for table_doc in table_docs:
        table_path = tables_dir / f"{_slugify_table_ref(table_doc.qualified_name)}.md"
        table_path.write_text(_render_table_doc(table_doc), encoding="utf-8")
        files_written.append(str(table_path))

    return ExportResult(table_refs=allowed_tables, files_written=files_written)


def _introspect_sqlite(database_url: str, requested_tables: list[str] | None) -> list[TableSchemaDoc]:
    sqlite_prefix = "sqlite:///"
    if not database_url.startswith(sqlite_prefix):
        raise ValueError("SQLite introspection requires a sqlite:/// URL.")

    db_path = database_url[len(sqlite_prefix) :]
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        if requested_tables:
            table_names = [_split_table_ref(table_ref)[1] for table_ref in requested_tables]
        else:
            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
            table_names = [row["name"] for row in cursor.fetchall()]

        table_docs: list[TableSchemaDoc] = []
        for table_name in table_names:
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = [
                ColumnInfo(
                    name=str(row["name"]),
                    data_type=str(row["type"] or ""),
                    nullable=not bool(row["notnull"]),
                    default=str(row["dflt_value"]) if row["dflt_value"] is not None else None,
                    is_primary_key=bool(row["pk"]),
                )
                for row in cursor.fetchall()
            ]

            cursor.execute(f'PRAGMA foreign_key_list("{table_name}")')
            foreign_keys_by_id: dict[int, dict[str, Any]] = {}
            for row in cursor.fetchall():
                entry = foreign_keys_by_id.setdefault(
                    int(row["id"]),
                    {
                        "table": str(row["table"]),
                        "from": [],
                        "to": [],
                    },
                )
                entry["from"].append(str(row["from"]))
                entry["to"].append(str(row["to"]))
            foreign_keys = [
                ForeignKeyInfo(
                    constrained_columns=value["from"],
                    referred_table=value["table"],
                    referred_schema=None,
                    referred_columns=value["to"],
                )
                for value in foreign_keys_by_id.values()
            ]

            cursor.execute(f'PRAGMA index_list("{table_name}")')
            indexes: list[IndexInfo] = []
            for index_row in cursor.fetchall():
                index_name = str(index_row["name"])
                cursor.execute(f'PRAGMA index_info("{index_name}")')
                index_columns = [str(column_row["name"]) for column_row in cursor.fetchall() if column_row["name"]]
                indexes.append(
                    IndexInfo(
                        name=index_name,
                        columns=index_columns,
                        unique=bool(index_row["unique"]),
                    )
                )

            table_docs.append(
                TableSchemaDoc(
                    schema_name=None,
                    table_name=table_name,
                    columns=columns,
                    foreign_keys=foreign_keys,
                    indexes=indexes,
                )
            )
        return table_docs
    finally:
        connection.close()


def _introspect_with_sqlalchemy(database_url: str, requested_tables: list[str] | None) -> list[TableSchemaDoc]:
    from sqlalchemy import create_engine, inspect

    engine = create_engine(database_url)
    inspector = inspect(engine)

    table_pairs: list[tuple[str | None, str]] = []
    if requested_tables:
        table_pairs = [_split_table_ref(table_ref) for table_ref in requested_tables]
    else:
        default_schema = getattr(inspector, "default_schema_name", None)
        candidate_schemas: list[str | None] = [None]
        if default_schema and default_schema not in candidate_schemas:
            candidate_schemas.append(default_schema)
        for schema_name in inspector.get_schema_names():
            if schema_name in SYSTEM_SCHEMAS or schema_name == default_schema:
                continue
            candidate_schemas.append(schema_name)

        seen_pairs: set[tuple[str | None, str]] = set()
        for schema_name in candidate_schemas:
            for table_name in inspector.get_table_names(schema=schema_name):
                pair = (schema_name, table_name)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    table_pairs.append(pair)

    table_docs: list[TableSchemaDoc] = []
    for schema_name, table_name in table_pairs:
        columns = [
            ColumnInfo(
                name=str(column["name"]),
                data_type=str(column.get("type", "")),
                nullable=bool(column.get("nullable", True)),
                default=str(column.get("default")) if column.get("default") is not None else None,
                is_primary_key=bool(column.get("primary_key")),
            )
            for column in inspector.get_columns(table_name, schema=schema_name)
        ]

        foreign_keys = [
            ForeignKeyInfo(
                constrained_columns=[str(value) for value in foreign_key.get("constrained_columns", [])],
                referred_table=str(foreign_key.get("referred_table", "")),
                referred_schema=str(foreign_key.get("referred_schema")) if foreign_key.get("referred_schema") else None,
                referred_columns=[str(value) for value in foreign_key.get("referred_columns", [])],
            )
            for foreign_key in inspector.get_foreign_keys(table_name, schema=schema_name)
        ]

        indexes = [
            IndexInfo(
                name=str(index.get("name", "")),
                columns=[str(value) for value in index.get("column_names", []) if value],
                unique=bool(index.get("unique")),
            )
            for index in inspector.get_indexes(table_name, schema=schema_name)
        ]

        table_docs.append(
            TableSchemaDoc(
                schema_name=schema_name,
                table_name=table_name,
                columns=columns,
                foreign_keys=foreign_keys,
                indexes=indexes,
            )
        )

    return table_docs


def export_schema_markdown(
    database_url: str,
    output_dir: str,
    database_label: str,
    allowed_tables: list[str] | None = None,
) -> ExportResult:
    requested_tables = [table.strip() for table in (allowed_tables or []) if table.strip()]

    if database_url.startswith("sqlite:///"):
        table_docs = _introspect_sqlite(database_url, requested_tables or None)
    else:
        table_docs = _introspect_with_sqlalchemy(database_url, requested_tables or None)

    return _write_markdown_docs(output_dir=output_dir, database_label=database_label, table_docs=table_docs)
