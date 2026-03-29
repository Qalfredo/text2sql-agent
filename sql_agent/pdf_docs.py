from __future__ import annotations

import os
import re
from pathlib import Path

from .schema_docs import ColumnDoc

DATA_TYPES = ("Integer", "String", "Float", "Datetime")
SKIP_STARTS = {
    "descripcion",
    "schema",
    "column",
    "table",
    "en",
    "notes",
    "pk",
    "is",
    "mongo",
}


class PdfDocsClient:
    def __init__(self, pdf_paths: list[str]):
        self.pdf_paths = [p for p in pdf_paths if p.strip()]

    @property
    def enabled(self) -> bool:
        return bool(self.pdf_paths)

    def load_docs(self) -> list[ColumnDoc]:
        if not self.enabled:
            return []

        docs: list[ColumnDoc] = []
        for pdf_path in self.pdf_paths:
            text = self._extract_pdf_text(pdf_path)
            docs.extend(self._parse_document(text))
        return docs

    def _extract_pdf_text(self, pdf_path: str) -> str:
        # Preferred backend: pypdf (portable in virtualenvs).
        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            return "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            pass

        # Fallback backend: macOS PDFKit via pyobjc.
        try:
            import objc
            from Foundation import NSBundle, NSURL

            bundle = NSBundle.bundleWithPath_("/System/Library/Frameworks/PDFKit.framework")
            if not bundle or not bundle.load():
                raise RuntimeError("Failed to load PDFKit framework.")

            pdf_document_class = objc.lookUpClass("PDFDocument")
            url = NSURL.fileURLWithPath_(pdf_path)
            doc = pdf_document_class.alloc().initWithURL_(url)
            if not doc:
                raise RuntimeError(f"Could not read PDF: {pdf_path}")

            pages: list[str] = []
            for i in range(doc.pageCount()):
                page = doc.pageAtIndex_(i)
                pages.append(page.string() or "")
            return "\n\n".join(pages)
        except Exception as exc:
            raise RuntimeError(
                "No PDF extraction backend available. Install 'pypdf' in your venv "
                "(`pip install pypdf`) or install pyobjc to use macOS PDFKit."
            ) from exc

    def _parse_document(self, text: str) -> list[ColumnDoc]:
        lines = [self._clean_line(line) for line in text.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            return []

        title = lines[0]
        table_name = self._infer_table_name(title)

        table_description = self._extract_table_description(lines)
        schema_name = self._extract_schema_name(lines)

        docs: list[ColumnDoc] = []
        if table_description:
            docs.append(
                ColumnDoc(
                    schema_name=schema_name,
                    table_name=table_name,
                    column_name=None,
                    description=table_description,
                )
            )

        column_lines = self._slice_column_section(lines)
        docs.extend(self._extract_columns(table_name=table_name, schema_name=schema_name, lines=column_lines))
        return docs

    def _extract_columns(
        self,
        table_name: str,
        schema_name: str | None,
        lines: list[str],
    ) -> list[ColumnDoc]:
        docs: list[ColumnDoc] = []

        current_col: str | None = None
        current_desc: list[str] = []
        current_type: str | None = None

        def flush() -> None:
            nonlocal current_col, current_desc, current_type
            if not current_col:
                return
            if current_type:
                description = " ".join(part.strip() for part in current_desc if part.strip()).strip()
                docs.append(
                    ColumnDoc(
                        schema_name=schema_name,
                        table_name=table_name,
                        column_name=current_col,
                        description=(description or f"Data type: {current_type}"),
                    )
                )
            current_col = None
            current_desc = []
            current_type = None

        for line in lines:
            maybe_name = self._new_column_name(line)
            if maybe_name:
                if maybe_name != current_col:
                    flush()
                current_col = maybe_name
                remainder = line[len(maybe_name) :].strip()
                if remainder:
                    rem_no_type, dtype = self._split_type(remainder)
                    if rem_no_type:
                        current_desc.append(rem_no_type)
                    if dtype:
                        current_type = dtype
                continue

            if not current_col:
                continue

            no_type, dtype = self._split_type(line)
            if no_type:
                # Ignore repeated Mongo reference echoes that add no semantic value.
                if no_type != current_col and no_type.lower() != f"{current_col}.unique_id":
                    current_desc.append(no_type)
            if dtype and not current_type:
                current_type = dtype

        flush()
        return docs

    @staticmethod
    def _clean_line(line: str) -> str:
        ascii_line = re.sub(r"[^\x00-\x7F]+", " ", line)
        ascii_line = re.sub(r"\s+", " ", ascii_line).strip()
        return ascii_line

    @staticmethod
    def _infer_table_name(title: str) -> str:
        title = title.strip().lower().replace("-", " ")
        title = re.sub(r"\s+", " ", title)
        if title == "car rental histories":
            return "car_rental_histories"
        return title.replace(" ", "_")

    @staticmethod
    def _extract_table_description(lines: list[str]) -> str:
        desc_start = None
        schema_start = None
        for idx, line in enumerate(lines):
            lowered = line.lower()
            if "de la tabla" in lowered and lowered.startswith("descrip"):
                desc_start = idx + 1
            if "schema de la tabla" in lowered:
                schema_start = idx
                break

        if desc_start is None:
            return ""

        desc_end = schema_start if schema_start is not None else len(lines)
        desc_parts = [line for line in lines[desc_start:desc_end] if line]
        return " ".join(desc_parts).strip()

    @staticmethod
    def _extract_schema_name(lines: list[str]) -> str | None:
        for line in lines:
            lowered = line.lower()
            if "pertenece" in lowered and ":" in line:
                return line.split(":", 1)[1].strip().lower()
        return None

    @staticmethod
    def _slice_column_section(lines: list[str]) -> list[str]:
        start = 0
        for idx, line in enumerate(lines):
            lowered = line.lower()
            if "table schema" in lowered:
                start = idx + 1
                break

        return lines[start:]

    @staticmethod
    def _split_type(text: str) -> tuple[str, str | None]:
        for dtype in DATA_TYPES:
            marker = re.search(rf"\b{dtype}\b", text, flags=re.IGNORECASE)
            if marker:
                before = text[: marker.start()].strip()
                return before, dtype
        return text.strip(), None

    @staticmethod
    def _new_column_name(line: str) -> str | None:
        match = re.match(r"^([a-z_][a-z0-9_]*)\b", line)
        if not match:
            return None

        candidate = match.group(1)
        if candidate in SKIP_STARTS:
            return None

        return candidate


def discover_default_pdf_paths() -> list[str]:
    docs_root = Path(os.getenv("PDF_DOCS_DIR", "docs/raw")).expanduser()
    if not docs_root.exists():
        return []
    return [str(path.resolve()) for path in sorted(docs_root.glob("*.pdf"))]
