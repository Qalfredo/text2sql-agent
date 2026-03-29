from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sql_agent.config import load_settings
from sql_agent.pdf_docs import PdfDocsClient, discover_default_pdf_paths


def main() -> None:
    settings = load_settings()
    paths = settings.pdf_doc_paths or discover_default_pdf_paths()
    if not paths:
        raise SystemExit("No PDF paths found. Set PDF_DOC_PATHS or place PDFs in default locations.")

    client = PdfDocsClient(paths)
    docs = client.load_docs()

    out = {
        "pdf_paths": paths,
        "entries": [asdict(doc) for doc in docs],
    }

    output_path = settings.schema_docs_json_path
    with open(output_path, "w", encoding="utf-8") as fp:
        json.dump(out, fp, indent=2, ensure_ascii=False)

    print(f"Wrote {output_path} with {len(docs)} documentation entries")


if __name__ == "__main__":
    main()
