from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlglot import expressions as exp
from sqlglot import parse_one

from .schema_docs import ColumnDoc, ContextDocument

FORBIDDEN_SQL_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|unload|vacuum|analyze|call)\b",
    flags=re.IGNORECASE,
)


@dataclass
class TableColumn:
    schema_name: str | None
    table_name: str
    column_name: str
    data_type: str


class SQLGuardError(ValueError):
    pass


class SQLDatabaseClient:
    def __init__(self, url: str, allowed_tables: list[str], sql_dialect: str, max_rows: int = 200):
        self.engine: Engine = create_engine(url)
        self.sql_dialect = sql_dialect
        self.max_rows = max_rows
        self.allowed_tables = self._normalize_allowed(allowed_tables)

    def _normalize_allowed(self, allowed_tables: list[str]) -> set[str]:
        normalized: set[str] = set()
        is_sqlite = self.sql_dialect.strip().lower() == "sqlite"
        for table in allowed_tables:
            cleaned = table.strip().lower()
            if not cleaned:
                continue
            # SQLite does not use Postgres-like schemas; tolerate schema-qualified
            # allowlists (e.g., public.customers) by collapsing to table name.
            if is_sqlite and "." in cleaned:
                cleaned = cleaned.split(".", 1)[1]
            normalized.add(cleaned)
        return normalized

    @staticmethod
    def _split_table_ref(table_ref: str) -> tuple[str | None, str]:
        if "." not in table_ref:
            return None, table_ref
        schema_name, table_name = table_ref.split(".", 1)
        return schema_name, table_name

    @staticmethod
    def _join_table_ref(schema_name: str | None, table_name: str) -> str:
        return f"{schema_name}.{table_name}" if schema_name else table_name

    def fetch_schema(self) -> dict[str, list[TableColumn]]:
        schema_map: dict[str, list[TableColumn]] = {}
        inspector = inspect(self.engine)

        for fqtn in sorted(self.allowed_tables):
            schema_name, table_name = self._split_table_ref(fqtn)
            raw_columns = inspector.get_columns(table_name, schema=schema_name)
            schema_map[self._join_table_ref(schema_name, table_name)] = [
                TableColumn(
                    schema_name=schema_name,
                    table_name=table_name,
                    column_name=str(column["name"]),
                    data_type=str(column["type"]),
                )
                for column in raw_columns
            ]

        return schema_map

    def execute_query(self, sql: str) -> tuple[list[str], list[tuple]]:
        cleaned = sql.strip().rstrip(";")
        self.validate_query(cleaned)

        with self.engine.connect() as conn:
            result = conn.execute(text(cleaned))
            rows = result.fetchmany(self.max_rows)
            headers = list(result.keys())
        return headers, [tuple(row) for row in rows]

    def validate_query(self, sql: str) -> None:
        if not sql:
            raise SQLGuardError("Query is empty.")

        lowered = sql.lower().lstrip()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            raise SQLGuardError("Only SELECT queries are allowed.")

        if ";" in sql:
            raise SQLGuardError("Only a single SQL statement is allowed.")

        if FORBIDDEN_SQL_RE.search(sql):
            raise SQLGuardError("Potentially mutating SQL detected; read-only queries only.")

        referenced_tables = self._extract_tables(sql)
        disallowed = [table for table in referenced_tables if table not in self.allowed_tables]
        if disallowed:
            raise SQLGuardError(
                "Query references non-allowlisted tables: " + ", ".join(sorted(set(disallowed)))
            )

    def _extract_tables(self, sql: str) -> set[str]:
        parsed = parse_one(sql, read=self.sql_dialect)
        found: set[str] = set()
        is_sqlite = self.sql_dialect.strip().lower() == "sqlite"

        for node in parsed.find_all(exp.Table):
            table_name = (node.name or "").strip().lower()
            schema_name = (node.db or "").strip().lower()
            if not table_name:
                continue
            if is_sqlite:
                found.add(table_name)
                continue
            if schema_name:
                found.add(self._join_table_ref(schema_name, table_name))
            else:
                matches = [
                    table
                    for table in self.allowed_tables
                    if table == table_name or table.endswith(f".{table_name}")
                ]
                if len(matches) == 1:
                    found.add(matches[0])
                else:
                    found.add(table_name)

        return found


def build_schema_context(
    schema_map: dict[str, list[TableColumn]],
    column_docs: list[ColumnDoc],
    context_docs: list[ContextDocument],
    database_label: str,
) -> str:
    doc_lookup: dict[tuple[str, str, str | None], str] = {}
    for doc in column_docs:
        key = (
            (doc.schema_name or "").lower(),
            doc.table_name.lower(),
            doc.column_name.lower() if doc.column_name else None,
        )
        doc_lookup[key] = doc.description

    lines: list[str] = [
        f"You can query only the following {database_label} tables.",
        "Use exact column names and prefer explicit schema-qualified table names when the database uses schemas.",
    ]

    for fqtn, columns in sorted(schema_map.items()):
        if "." in fqtn:
            schema_name, table_name = fqtn.split(".", 1)
        else:
            schema_name, table_name = "", fqtn
        table_desc = doc_lookup.get((schema_name, table_name, None)) or doc_lookup.get(("", table_name, None))

        lines.append(f"\nTable: {fqtn}")
        if table_desc:
            lines.append(f"Table description: {table_desc}")

        for column in columns:
            col_desc = doc_lookup.get((schema_name, table_name, column.column_name.lower())) or doc_lookup.get(
                ("", table_name, column.column_name.lower())
            )
            if col_desc:
                lines.append(f"- {column.column_name} ({column.data_type}) - {col_desc}")
            else:
                lines.append(f"- {column.column_name} ({column.data_type})")

    if context_docs:
        lines.append("\nAdditional database documentation:")
        for document in context_docs:
            lines.append(f"\nSource: {document.source_name}\n{document.content}")

    return "\n".join(lines)
