from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any, Iterable


def normalize_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(round(value, 10))
    if isinstance(value, float):
        return float(round(value, 10))
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def normalize_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(normalize_scalar(v) for v in row)


def normalize_text(text_value: str) -> str:
    lowered = text_value.lower()
    return re.sub(r"\s+", " ", lowered).strip()


def headers_match(predicted_headers: list[str], gold_headers: list[str]) -> bool:
    return list(predicted_headers) == list(gold_headers)


def exact_match(
    predicted_headers: list[str],
    predicted_rows: list[tuple[Any, ...]],
    gold_headers: list[str],
    gold_rows: list[tuple[Any, ...]],
) -> bool:
    return headers_match(predicted_headers, gold_headers) and [
        normalize_row(row) for row in predicted_rows
    ] == [normalize_row(row) for row in gold_rows]


def unordered_match(
    predicted_headers: list[str],
    predicted_rows: list[tuple[Any, ...]],
    gold_headers: list[str],
    gold_rows: list[tuple[Any, ...]],
) -> bool:
    return headers_match(predicted_headers, gold_headers) and Counter(
        normalize_row(row) for row in predicted_rows
    ) == Counter(normalize_row(row) for row in gold_rows)


def scalar_text_match(agent_answer: str, gold_rows: list[tuple[Any, ...]]) -> bool:
    if not agent_answer or len(gold_rows) != 1 or len(gold_rows[0]) != 1:
        return False
    gold_value_text = normalize_text(str(normalize_scalar(gold_rows[0][0])))
    return gold_value_text in normalize_text(agent_answer)


def execution_accuracy(results: Iterable[Any]) -> float:
    result_list = list(results)
    if not result_list:
        return 0.0
    return sum(1 for result in result_list if bool(getattr(result, "passed", False))) / len(result_list)


def latency_percentile(latencies_ms: list[float], percentile: float) -> float:
    if not latencies_ms:
        return 0.0
    ordered = sorted(latencies_ms)
    rank = max(0, min(len(ordered) - 1, math.ceil((percentile / 100) * len(ordered)) - 1))
    return float(round(ordered[rank], 3))


def sql_validity_rate(results: Iterable[Any]) -> float:
    result_list = list(results)
    if not result_list:
        return 0.0
    valid = sum(1 for result in result_list if int(getattr(result, "successful_sql_attempt_count", 0)) > 0)
    return valid / len(result_list)


def summarize_results(results: list[Any]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if bool(getattr(result, "passed", False)))
    exact = sum(1 for result in results if bool(getattr(result, "exact_match", False)))
    unordered = sum(1 for result in results if bool(getattr(result, "unordered_match", False)))
    scalar = sum(1 for result in results if bool(getattr(result, "scalar_text_match", False)))
    errored = sum(1 for result in results if bool(getattr(result, "agent_error", None)))

    by_difficulty: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0})
    for result in results:
        bucket = by_difficulty[str(getattr(result, "difficulty", "unknown"))]
        bucket["total"] += 1
        if bool(getattr(result, "passed", False)):
            bucket["passed"] += 1

    latencies = [float(getattr(result, "duration_ms", 0.0) or 0.0) for result in results]

    return {
        "total_items": total,
        "passed_items": passed,
        "pass_rate": (passed / total) if total else 0.0,
        "execution_accuracy": execution_accuracy(results),
        "exact_match_count": exact,
        "unordered_match_count": unordered,
        "scalar_text_match_count": scalar,
        "agent_error_count": errored,
        "latency_p50_ms": latency_percentile(latencies, 50),
        "latency_p95_ms": latency_percentile(latencies, 95),
        "sql_validity_rate": sql_validity_rate(results),
        "by_difficulty": {
            key: {
                "total": value["total"],
                "passed": value["passed"],
                "pass_rate": (value["passed"] / value["total"]) if value["total"] else 0.0,
            }
            for key, value in sorted(by_difficulty.items())
        },
    }
