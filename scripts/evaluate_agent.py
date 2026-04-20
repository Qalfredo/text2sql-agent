#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sql_agent.config import load_settings
from sql_agent.evaluation import BenchmarkRunner, ReportGenerator


def evaluate(dataset_path: Path, output_dir: Path, max_items: int | None):
    load_dotenv(".env", override=False)
    settings = load_settings()
    runner = BenchmarkRunner(
        agent_config=settings,
        dataset=dataset_path,
        output_dir=output_dir,
        max_workers=1,
        timeout_per_question=60,
    )
    benchmark_result = runner.run(max_items=max_items)

    report_generator = ReportGenerator(benchmark_result)
    json_path = report_generator.write_json(output_dir / f"agent_eval_{benchmark_result.run_id}.json")
    csv_path = report_generator.write_csv(output_dir / f"agent_eval_{benchmark_result.run_id}.csv")

    total = benchmark_result.summary["total_items"]
    passed = benchmark_result.summary["passed_items"]
    print(f"Evaluated {total} items")
    print(f"Passed: {passed}/{total} ({benchmark_result.summary['pass_rate']:.2%})")
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")
    print(f"Run directory: {benchmark_result.run_dir}")

    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the text-to-SQL agent against a benchmark dataset.")
    parser.add_argument(
        "--dataset",
        default="chinook_benchmark_v1.json.rtf",
        help="Path to benchmark dataset (.json, .rtf with JSON content, or .csv).",
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
    parser.add_argument(
        "--timeout-per-question",
        type=int,
        default=60,
        help="Per-question timeout in seconds.",
    )
    args = parser.parse_args()

    load_dotenv(".env", override=False)
    settings = load_settings()
    runner = BenchmarkRunner(
        agent_config=settings,
        dataset=Path(args.dataset).expanduser().resolve(),
        output_dir=Path(args.output_dir).expanduser().resolve(),
        max_workers=1,
        timeout_per_question=args.timeout_per_question,
    )
    benchmark_result = runner.run(max_items=args.max_items)

    report_generator = ReportGenerator(benchmark_result)
    json_path = report_generator.write_json(runner.output_dir / f"agent_eval_{benchmark_result.run_id}.json")
    csv_path = report_generator.write_csv(runner.output_dir / f"agent_eval_{benchmark_result.run_id}.csv")

    total = benchmark_result.summary["total_items"]
    passed = benchmark_result.summary["passed_items"]
    print(f"Evaluated {total} items")
    print(f"Passed: {passed}/{total} ({benchmark_result.summary['pass_rate']:.2%})")
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")
    print(f"Run directory: {benchmark_result.run_dir}")


if __name__ == "__main__":
    main()
