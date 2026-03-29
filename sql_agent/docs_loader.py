from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .coda_docs import CodaDocsClient
from .config import Settings
from .markdown_docs import MarkdownDocsClient
from .pdf_docs import PdfDocsClient, discover_default_pdf_paths
from .schema_docs import ColumnDoc, ContextDocument


@dataclass(frozen=True)
class DocumentationBundle:
    column_docs: list[ColumnDoc]
    context_docs: list[ContextDocument]


def _normalize_paths(paths: list[str]) -> list[str]:
    return [str(Path(p).expanduser().resolve()) for p in paths]


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


def _load_cached_docs(cache_path: str, expected_pdf_paths: list[str]) -> list[ColumnDoc]:
    path = Path(cache_path)
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    cached_paths = [str(p) for p in payload.get("pdf_paths", []) if str(p).strip()]
    if cached_paths and expected_pdf_paths:
        if _normalize_paths(cached_paths) != _normalize_paths(expected_pdf_paths):
            return []

    entries = payload.get("entries", [])
    docs: list[ColumnDoc] = []
    for entry in entries:
        docs.append(
            ColumnDoc(
                schema_name=entry.get("schema_name"),
                table_name=entry.get("table_name", ""),
                column_name=entry.get("column_name"),
                description=entry.get("description", ""),
            )
        )
    return docs


def load_documentation_bundle(settings: Settings) -> DocumentationBundle:
    pdf_paths = settings.pdf_doc_paths or discover_default_pdf_paths()
    cached_docs = _load_cached_docs(settings.schema_docs_json_path, pdf_paths)

    pdf_docs: list[ColumnDoc] = []
    if not cached_docs and pdf_paths:
        try:
            pdf_docs = PdfDocsClient(pdf_paths).load_docs()
        except Exception:
            pdf_docs = []

    coda_docs = CodaDocsClient(settings).load_docs()
    markdown_docs = MarkdownDocsClient(settings.markdown_docs_dir).load_docs()

    return DocumentationBundle(
        column_docs=_dedupe_column_docs([*cached_docs, *pdf_docs, *coda_docs]),
        context_docs=markdown_docs,
    )
