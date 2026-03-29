from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnDoc:
    schema_name: str | None
    table_name: str
    column_name: str | None
    description: str


@dataclass(frozen=True)
class ContextDocument:
    source_name: str
    content: str
