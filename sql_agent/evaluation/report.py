from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


def _safe_jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_safe_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe_jsonable(item) for key, item in value.items()}
    return str(value)


@dataclass
class BenchmarkQuestionResult:
    item_id: str
    question: str
    category: str
    difficulty: str
    gold_sql: str
    gold_headers: list[str]
    gold_rows: list[list[Any]]
    gold_error: str | None
    agent_answer: str
    agent_error: str | None
    duration_ms: float
    sql_attempt_count: int
    successful_sql_attempt_count: int
    final_sql: str | None
    final_sql_headers: list[str]
    final_sql_rows: list[list[Any]]
    headers_match: bool
    exact_match: bool
    unordered_match: bool
    scalar_text_match: bool
    passed: bool
    sql_attempts: list[dict[str, Any]] = field(default_factory=list)
    token_usage: dict[str, int] | None = None
    agent_state: str | None = None
    step_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["id"] = payload.pop("item_id")
        payload["pass"] = payload.pop("passed")
        return _safe_jsonable(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BenchmarkQuestionResult":
        copied = dict(payload)
        copied["item_id"] = copied.pop("item_id", None) or copied.pop("id")
        copied["passed"] = copied.pop("passed", None)
        if copied["passed"] is None:
            copied["passed"] = copied.pop("pass")
        return cls(**copied)


@dataclass
class BenchmarkResult:
    run_id: str
    generated_at_utc: str
    dataset_path: str
    config_hash: str
    config_label: str
    run_dir: str
    summary: dict[str, Any]
    results: list[BenchmarkQuestionResult]
    settings: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                **_safe_jsonable(self.summary),
                "run_id": self.run_id,
                "generated_at_utc": self.generated_at_utc,
                "dataset_path": self.dataset_path,
                "config_hash": self.config_hash,
                "config_label": self.config_label,
                "run_dir": self.run_dir,
                "settings": _safe_jsonable(self.settings),
            },
            "results": [result.to_dict() for result in self.results],
        }

    def to_dataframe(self):
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("pandas is required for BenchmarkResult.to_dataframe(). Install `.[eval]`.") from exc

        return pd.DataFrame([result.to_dict() for result in self.results])


class ReportGenerator:
    def __init__(self, benchmark_result: BenchmarkResult):
        self.benchmark_result = benchmark_result

    def write_json(self, path: str | Path) -> Path:
        output_path = Path(path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.benchmark_result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path

    def write_summary(self, path: str | Path) -> Path:
        output_path = Path(path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.benchmark_result.summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path

    def write_csv(self, path: str | Path) -> Path:
        output_path = Path(path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
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
            "agent_state",
            "step_count",
        ]

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=csv_fields)
            writer.writeheader()
            for row in self.benchmark_result.results:
                payload = row.to_dict()
                writer.writerow({field: payload.get(field) for field in csv_fields})
        return output_path

    def write_html(self, path: str | Path) -> Path:
        output_path = Path(path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        summary = self.benchmark_result.summary

        rows_html = "\n".join(
            (
                "<tr>"
                f"<td>{escape(result.item_id)}</td>"
                f"<td>{escape(result.difficulty)}</td>"
                f"<td>{escape(result.category)}</td>"
                f"<td>{escape(result.question)}</td>"
                f"<td>{'PASS' if result.passed else 'FAIL'}</td>"
                f"<td>{result.duration_ms:.1f}</td>"
                f"<td>{escape(result.final_sql or '')}</td>"
                "</tr>"
            )
            for result in self.benchmark_result.results
        )

        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Benchmark Report {escape(self.benchmark_result.run_id)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d0d7de; padding: 0.5rem; vertical-align: top; text-align: left; }}
    th {{ background: #f6f8fa; }}
    code {{ white-space: pre-wrap; }}
  </style>
</head>
<body>
  <h1>Benchmark Report</h1>
  <p><strong>Run ID:</strong> {escape(self.benchmark_result.run_id)}</p>
  <p><strong>Generated:</strong> {escape(self.benchmark_result.generated_at_utc)}</p>
  <p><strong>Dataset:</strong> {escape(self.benchmark_result.dataset_path)}</p>
  <p><strong>Pass rate:</strong> {summary.get('pass_rate', 0.0):.2%}</p>
  <p><strong>Latency p50 / p95:</strong> {summary.get('latency_p50_ms', 0.0):.1f} ms / {summary.get('latency_p95_ms', 0.0):.1f} ms</p>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Difficulty</th>
        <th>Category</th>
        <th>Question</th>
        <th>Pass</th>
        <th>Latency (ms)</th>
        <th>Final SQL</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>
"""
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def write_run_artifacts(self, run_dir: str | Path) -> dict[str, Path]:
        output_dir = Path(run_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        return {
            "json": self.write_json(output_dir / "benchmark_result.json"),
            "csv": self.write_csv(output_dir / "benchmark_result.csv"),
            "html": self.write_html(output_dir / "benchmark_report.html"),
            "summary": self.write_summary(output_dir / "summary.json"),
        }


def build_result(
    *,
    run_id: str,
    dataset_path: str,
    config_hash: str,
    config_label: str,
    run_dir: str,
    summary: dict[str, Any],
    results: list[BenchmarkQuestionResult],
    settings: dict[str, Any],
) -> BenchmarkResult:
    return BenchmarkResult(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dataset_path=dataset_path,
        config_hash=config_hash,
        config_label=config_label,
        run_dir=run_dir,
        summary=summary,
        results=results,
        settings=settings,
    )
