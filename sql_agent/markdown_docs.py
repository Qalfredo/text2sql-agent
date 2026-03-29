from __future__ import annotations

from pathlib import Path

from .schema_docs import ContextDocument


class MarkdownDocsClient:
    def __init__(self, docs_dir: str | None):
        self.docs_dir = docs_dir.strip() if docs_dir else ""

    @property
    def enabled(self) -> bool:
        return bool(self.docs_dir)

    def load_docs(self) -> list[ContextDocument]:
        if not self.enabled:
            return []

        root = Path(self.docs_dir).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return []

        documents: list[ContextDocument] = []
        for path in sorted(root.rglob("*.md")):
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            documents.append(
                ContextDocument(
                    source_name=str(path.relative_to(root)),
                    content=content,
                )
            )
        return documents
