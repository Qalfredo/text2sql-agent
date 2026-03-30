from __future__ import annotations

from dataclasses import dataclass

from .coda_docs import CodaDocsClient
from .config import Settings
from .markdown_docs import MarkdownDocsClient
from .schema_docs import ColumnDoc, ContextDocument


@dataclass(frozen=True)
class DocumentationBundle:
    column_docs: list[ColumnDoc]
    context_docs: list[ContextDocument]


def _dedupe_column_docs(docs: list[ColumnDoc]) -> list[ColumnDoc]:
    unique: dict[tuple[str, str, str | None], ColumnDoc] = {}
    for doc in docs:
        key = (
            (doc.schema_name or "").lower(),
            doc.table_name.lower(),
            doc.column_name.lower() if doc.column_name else None,
        )
        unique[key] = doc
    return list(unique.values())


def load_documentation_bundle(settings: Settings) -> DocumentationBundle:
    coda_docs = CodaDocsClient(settings).load_docs()
    markdown_docs = MarkdownDocsClient(settings.markdown_docs_dir).load_docs()

    return DocumentationBundle(
        column_docs=_dedupe_column_docs(coda_docs),
        context_docs=markdown_docs,
    )
