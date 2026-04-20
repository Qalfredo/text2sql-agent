from __future__ import annotations

from pathlib import Path

from sql_agent.config import Settings

from .report import BenchmarkResult
from .runner import BenchmarkRunner


class ComparisonSuite:
    def __init__(
        self,
        dataset: str | Path,
        output_dir: str | Path = "eval_results",
        max_workers: int = 1,
        timeout_per_question: int = 60,
        resume: bool = True,
    ):
        self.dataset = Path(dataset).expanduser().resolve()
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.max_workers = max_workers
        self.timeout_per_question = timeout_per_question
        self.resume = resume
        self._configs: list[tuple[str, Settings]] = []

    def add_config(self, label: str, settings: Settings) -> None:
        self._configs.append((label, settings))

    def run_all(self, max_items: int | None = None) -> dict[str, BenchmarkResult]:
        results: dict[str, BenchmarkResult] = {}
        for label, settings in self._configs:
            runner = BenchmarkRunner(
                agent_config=settings,
                dataset=self.dataset,
                output_dir=self.output_dir,
                max_workers=self.max_workers,
                timeout_per_question=self.timeout_per_question,
                resume=self.resume,
                config_label=label,
            )
            results[label] = runner.run(max_items=max_items)
        return results

    def compare(self, results: dict[str, BenchmarkResult]):
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("pandas is required for ComparisonSuite.compare(). Install `.[eval]`.") from exc

        rows = []
        for label, result in results.items():
            summary = result.summary
            rows.append(
                {
                    "config": label,
                    "model_provider": result.settings.get("model_provider"),
                    "model_id": result.settings.get("model_id"),
                    "pass_rate": summary.get("pass_rate"),
                    "execution_accuracy": summary.get("execution_accuracy"),
                    "exact_match_count": summary.get("exact_match_count"),
                    "unordered_match_count": summary.get("unordered_match_count"),
                    "scalar_text_match_count": summary.get("scalar_text_match_count"),
                    "latency_p50_ms": summary.get("latency_p50_ms"),
                    "latency_p95_ms": summary.get("latency_p95_ms"),
                    "sql_validity_rate": summary.get("sql_validity_rate"),
                    "total_items": summary.get("total_items"),
                    "run_id": result.run_id,
                }
            )
        return pd.DataFrame(rows).sort_values(by=["pass_rate", "execution_accuracy"], ascending=False)
