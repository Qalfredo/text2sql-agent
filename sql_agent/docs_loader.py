from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .markdown_docs import MarkdownDocsClient
from .schema_docs import ColumnDoc, ContextDocument


@dataclass(frozen=True)
class DocumentationBundle:
    column_docs: list[ColumnDoc]
    context_docs: list[ContextDocument]


def load_documentation_bundle(settings: Settings) -> DocumentationBundle:
    markdown_docs = MarkdownDocsClient(settings.markdown_docs_dir).load_docs()

    return DocumentationBundle(
        column_docs=[],
        context_docs=markdown_docs,
    )
