from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvalItem:
    item_id: str
    question: str
    gold_sql: str
    category: str = "unknown"
    difficulty: str = "unknown"


def _rtf_to_text(path: Path) -> str:
    try:
        proc = subprocess.run(
            ["textutil", "-convert", "txt", "-stdout", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("textutil is required to parse .rtf datasets on this machine.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to convert RTF dataset: {exc.stderr or exc.stdout}") from exc

    return proc.stdout


def _load_json_stream(raw_text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    idx = 0
    records: list[dict[str, Any]] = []

    while idx < len(raw_text):
        while idx < len(raw_text) and raw_text[idx].isspace():
            idx += 1
        if idx >= len(raw_text):
            break

        obj, end = decoder.raw_decode(raw_text, idx)
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    records.append(item)
        elif isinstance(obj, dict):
            records.append(obj)
        idx = end

    return records


def _normalize_records(records: list[dict[str, Any]]) -> list[EvalItem]:
    items: list[EvalItem] = []
    for idx, row in enumerate(records, start=1):
        question = str(row.get("question") or "").strip()
        gold_sql = str(row.get("gold_sql") or row.get("sql") or "").strip()
        if not question or not gold_sql:
            continue

        item_id = str(row.get("id") or row.get("item_id") or f"item_{idx:03d}")
        items.append(
            EvalItem(
                item_id=item_id,
                question=question,
                gold_sql=gold_sql,
                category=str(row.get("category") or "unknown"),
                difficulty=str(row.get("difficulty") or "unknown"),
            )
        )

    if not items:
        raise ValueError("Dataset parsed but no valid rows with question + gold_sql were found.")
    return items


def _load_csv_dataset(path: Path) -> list[EvalItem]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return _normalize_records(list(reader))


def load_dataset(path: str | Path) -> list[EvalItem]:
    dataset_path = Path(path).expanduser().resolve()
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    suffix = dataset_path.suffix.lower()
    if suffix == ".csv":
        return _load_csv_dataset(dataset_path)

    if suffix == ".rtf":
        raw_text = _rtf_to_text(dataset_path)
    else:
        raw_text = dataset_path.read_text(encoding="utf-8")

    records = _load_json_stream(raw_text)
    if not records:
        raise ValueError("No records found in dataset.")
    return _normalize_records(records)
