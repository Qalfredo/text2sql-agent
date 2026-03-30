#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from sql_agent.agent import build_agent_runtime
from sql_agent.config import load_settings


@dataclass
class EvalItem:
    item_id: str
    question: str
    gold_sql: str
    category: str
    difficulty: str


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


def load_dataset(path: Path) -> list[EvalItem]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if path.suffix.lower() == ".rtf":
        raw_text = _rtf_to_text(path)
    else:
        raw_text = path.read_text(encoding="utf-8")

    records = _load_json_stream(raw_text)
    if not records:
        raise ValueError("No records found in dataset.")

    items: list[EvalItem] = []
    for idx, row in enumerate(records, start=1):
        item_id = str(row.get("id") or f"item_{idx:03d}")
        question = str(row.get("question") or "").strip()
        gold_sql = str(row.get("gold_sql") or "").strip()
        category = str(row.get("category") or "unknown")
        difficulty = str(row.get("difficulty") or "unknown")
        if not question or not gold_sql:
            continue
        items.append(EvalItem(item_id=item_id, question=question, gold_sql=gold_sql, category=category, difficulty=difficulty))

    if not items:
        raise ValueError("Dataset parsed but no valid rows with question + gold_sql were found.")

    return items


def _normalize_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(round(value, 10))
    if isinstance(value, float):
        return float(round(value, 10))
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _normalize_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(_normalize_scalar(v) for v in row)


def _normalize_text(text_value: str) -> str:
    lowered = text_value.lower()
    collapsed = re.sub(r"\s+", " ", lowered).strip()
    return collapsed


def _execute_sql(engine, sql_query: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql_query.strip().rstrip(";")))
        headers = [str(c) for c in result.keys()]
        rows = [tuple(row) for row in result.fetchall()]
    return headers, rows


def _safe_jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_safe_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_jsonable(v) for k, v in value.items()}
    return str(value)


def evaluate(dataset_path: Path, output_dir: Path, max_items: int | None) -> tuple[Path, Path]:
    load_dotenv(".env", override=True)
    settings = load_settings()
    runtime = build_agent_runtime(settings)
    engine = create_engine(settings.database_url)

    items = load_dataset(dataset_path)
    if max_items is not None:
        items = items[:max_items]

    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    results: list[dict[str, Any]] = []

    original_execute_query = runtime.database_client.execute_query

    for item in items:
        sql_attempts: list[dict[str, Any]] = []

        def capture_execute_query(sql_query: str):
            attempt: dict[str, Any] = {
                "sql": sql_query,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
            attempt_start = time.perf_counter()
            try:
                headers, rows = original_execute_query(sql_query)
                attempt["ok"] = True
                attempt["headers"] = headers
                attempt["rows"] = [_safe_jsonable(list(r)) for r in rows]
                attempt["row_count"] = len(rows)
                return headers, rows
            except Exception as exc:  # noqa: BLE001
                attempt["ok"] = False
                attempt["error"] = str(exc)
                raise
            finally:
                attempt["duration_ms"] = round((time.perf_counter() - attempt_start) * 1000, 3)
                sql_attempts.append(attempt)

        runtime.database_client.execute_query = capture_execute_query  # type: ignore[method-assign]

        started_at = time.perf_counter()
        agent_answer = ""
        agent_error = None

        try:
            agent_answer = runtime.run(item.question)
        except Exception as exc:  # noqa: BLE001
            agent_error = str(exc)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)

        gold_headers: list[str] = []
        gold_rows: list[tuple[Any, ...]] = []
        gold_error = None
        try:
            gold_headers, gold_rows = _execute_sql(engine, item.gold_sql)
        except Exception as exc:  # noqa: BLE001
            gold_error = str(exc)

        successful_sql = [a for a in sql_attempts if a.get("ok")]
        final_sql = successful_sql[-1] if successful_sql else None

        predicted_headers = list(final_sql.get("headers", [])) if final_sql else []
        predicted_rows = [tuple(r) for r in final_sql.get("rows", [])] if final_sql else []

        headers_match = predicted_headers == gold_headers
        exact_match = False
        unordered_match = False
        scalar_text_match = False

        if final_sql and gold_error is None:
            norm_pred_rows = [_normalize_row(r) for r in predicted_rows]
            norm_gold_rows = [_normalize_row(r) for r in gold_rows]

            exact_match = headers_match and norm_pred_rows == norm_gold_rows
            unordered_match = headers_match and Counter(norm_pred_rows) == Counter(norm_gold_rows)

            if len(gold_rows) == 1 and len(gold_rows[0]) == 1 and agent_answer:
                gold_value_text = _normalize_text(str(_normalize_scalar(gold_rows[0][0])))
                answer_text = _normalize_text(agent_answer)
                scalar_text_match = gold_value_text in answer_text

        pass_result = bool(exact_match or unordered_match or scalar_text_match)

        result_row = {
            "id": item.item_id,
            "question": item.question,
            "category": item.category,
            "difficulty": item.difficulty,
            "gold_sql": item.gold_sql,
            "gold_headers": gold_headers,
            "gold_rows": [_safe_jsonable(list(r)) for r in gold_rows],
            "gold_error": gold_error,
            "agent_answer": agent_answer,
            "agent_error": agent_error,
            "duration_ms": duration_ms,
            "sql_attempt_count": len(sql_attempts),
            "successful_sql_attempt_count": len(successful_sql),
            "final_sql": final_sql.get("sql") if final_sql else None,
            "final_sql_headers": predicted_headers,
            "final_sql_rows": [_safe_jsonable(list(r)) for r in predicted_rows],
            "headers_match": headers_match,
            "exact_match": exact_match,
            "unordered_match": unordered_match,
            "scalar_text_match": scalar_text_match,
            "pass": pass_result,
            "sql_attempts": sql_attempts,
        }
        results.append(result_row)

    runtime.database_client.execute_query = original_execute_query  # type: ignore[method-assign]

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    exact = sum(1 for r in results if r["exact_match"])
    unordered = sum(1 for r in results if r["unordered_match"])
    scalar = sum(1 for r in results if r["scalar_text_match"])
    errored = sum(1 for r in results if r["agent_error"])

    by_difficulty: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in results:
        bucket = by_difficulty[r["difficulty"]]
        bucket["total"] += 1
        if r["pass"]:
            bucket["passed"] += 1

    summary = {
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path),
        "total_items": total,
        "passed_items": passed,
        "pass_rate": (passed / total) if total else 0.0,
        "exact_match_count": exact,
        "unordered_match_count": unordered,
        "scalar_text_match_count": scalar,
        "agent_error_count": errored,
        "by_difficulty": {
            k: {
                "total": v["total"],
                "passed": v["passed"],
                "pass_rate": (v["passed"] / v["total"]) if v["total"] else 0.0,
            }
            for k, v in sorted(by_difficulty.items())
        },
    }

    json_path = output_dir / f"agent_eval_{run_id}.json"
    csv_path = output_dir / f"agent_eval_{run_id}.csv"

    payload = {
        "summary": summary,
        "results": results,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_fields = [
        "id",
        "difficulty",
        "category",
        "question",
        "gold_sql",
        "final_sql",
        "agent_answer",
        "agent_error",
        "gold_error",
        "duration_ms",
        "sql_attempt_count",
        "successful_sql_attempt_count",
        "headers_match",
        "exact_match",
        "unordered_match",
        "scalar_text_match",
        "pass",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in results:
            writer.writerow({field: row.get(field) for field in csv_fields})

    print(f"Evaluated {total} items")
    print(f"Passed: {passed}/{total} ({summary['pass_rate']:.2%})")
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")

    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the text-to-SQL agent against a benchmark dataset.")
    parser.add_argument(
        "--dataset",
        default="chinook_benchmark_v1.json.rtf",
        help="Path to benchmark dataset (.json or .rtf with JSON content).",
    )
    parser.add_argument(
        "--output-dir",
        default="eval_results",
        help="Directory where evaluation reports are written.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Optional cap for number of benchmark rows (useful for quick smoke tests).",
    )
    args = parser.parse_args()

    evaluate(
        dataset_path=Path(args.dataset).expanduser().resolve(),
        output_dir=Path(args.output_dir).expanduser().resolve(),
        max_items=args.max_items,
    )


if __name__ == "__main__":
    main()
