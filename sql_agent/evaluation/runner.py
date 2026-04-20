from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from sql_agent.agent import AgentRuntime, build_agent_runtime
from sql_agent.config import Settings

from .dataset import EvalItem, load_dataset
from .metrics import exact_match, headers_match, scalar_text_match, summarize_results, unordered_match
from .report import BenchmarkQuestionResult, ReportGenerator, build_result


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


def _execute_sql(engine, sql_query: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql_query.strip().rstrip(";")))
        headers = [str(column) for column in result.keys()]
        rows = [tuple(row) for row in result.fetchall()]
    return headers, rows


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "run"


def _settings_snapshot(settings: Settings) -> dict[str, Any]:
    payload = asdict(settings)
    for secret_key in ("openai_api_key", "hf_token", "google_api_key"):
        if payload.get(secret_key):
            payload[secret_key] = "***"
    return payload


def _settings_hash(settings: Settings) -> str:
    payload = json.dumps(_settings_snapshot(settings), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


class BenchmarkRunner:
    def __init__(
        self,
        agent_config: Settings,
        dataset: str | Path,
        output_dir: str | Path = "eval_results",
        max_workers: int = 1,
        timeout_per_question: int = 60,
        resume: bool = True,
        run_id: str | None = None,
        config_label: str | None = None,
    ):
        self.agent_config = agent_config
        self.dataset_path = Path(dataset).expanduser().resolve()
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.max_workers = max(1, max_workers)
        self.timeout_per_question = timeout_per_question
        self.resume = resume
        self.config_hash = _settings_hash(agent_config)
        self.config_label = config_label or f"{agent_config.model_provider}:{agent_config.model_id}"
        default_run_id = f"{_slugify(self.dataset_path.stem)}-{_slugify(self.config_label)}-{self.config_hash[:8]}"
        self.run_id = run_id or default_run_id
        self.run_dir = self.output_dir / self.run_id
        self.items_dir = self.run_dir / "items"

    def _write_manifest(self, *, total_items: int, completed_items: int) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.run_dir / "manifest.json"
        manifest = {
            "run_id": self.run_id,
            "config_label": self.config_label,
            "config_hash": self.config_hash,
            "dataset_path": str(self.dataset_path),
            "max_workers": self.max_workers,
            "timeout_per_question": self.timeout_per_question,
            "resume": self.resume,
            "completed_items": completed_items,
            "total_items": total_items,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "settings": _settings_snapshot(self.agent_config),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _persist_question_result(self, result: BenchmarkQuestionResult) -> None:
        self.items_dir.mkdir(parents=True, exist_ok=True)
        item_path = self.items_dir / f"{result.item_id}.json"
        item_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_existing_results(self) -> dict[str, BenchmarkQuestionResult]:
        if not self.resume or not self.items_dir.exists():
            return {}
        results: dict[str, BenchmarkQuestionResult] = {}
        for item_file in sorted(self.items_dir.glob("*.json")):
            payload = json.loads(item_file.read_text(encoding="utf-8"))
            result = BenchmarkQuestionResult.from_dict(payload)
            results[result.item_id] = result
        return results

    def _run_agent_with_timeout(self, runtime: AgentRuntime, question: str):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(runtime.run_full, question)
            try:
                return future.result(timeout=self.timeout_per_question)
            except FuturesTimeoutError as exc:
                raise TimeoutError(f"Timed out after {self.timeout_per_question} seconds.") from exc

    def _evaluate_item(
        self,
        item: EvalItem,
        runtime: AgentRuntime | None = None,
        engine=None,
    ) -> BenchmarkQuestionResult:
        local_runtime = runtime or build_agent_runtime(self.agent_config)
        local_engine = engine or create_engine(self.agent_config.database_url)
        dispose_engine = engine is None

        sql_attempts: list[dict[str, Any]] = []
        original_execute_query = local_runtime.database_client.execute_query

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
                attempt["rows"] = [_safe_jsonable(list(row)) for row in rows]
                attempt["row_count"] = len(rows)
                return headers, rows
            except Exception as exc:  # noqa: BLE001
                attempt["ok"] = False
                attempt["error"] = str(exc)
                raise
            finally:
                attempt["duration_ms"] = round((time.perf_counter() - attempt_start) * 1000, 3)
                sql_attempts.append(attempt)

        local_runtime.database_client.execute_query = capture_execute_query  # type: ignore[method-assign]

        started_at = time.perf_counter()
        agent_answer = ""
        agent_error = None
        token_usage = None
        agent_state = None
        step_count = 0

        try:
            run_result = self._run_agent_with_timeout(local_runtime, item.question)
            agent_answer = str(run_result.output or "")
            agent_state = run_result.state
            step_count = len(run_result.steps or [])
            if run_result.token_usage:
                token_usage = {
                    "input_tokens": int(run_result.token_usage.input_tokens),
                    "output_tokens": int(run_result.token_usage.output_tokens),
                    "total_tokens": int(run_result.token_usage.input_tokens + run_result.token_usage.output_tokens),
                }
        except Exception as exc:  # noqa: BLE001
            agent_error = str(exc)
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
            local_runtime.database_client.execute_query = original_execute_query  # type: ignore[method-assign]

        gold_headers: list[str] = []
        gold_rows: list[tuple[Any, ...]] = []
        gold_error = None
        try:
            gold_headers, gold_rows = _execute_sql(local_engine, item.gold_sql)
        except Exception as exc:  # noqa: BLE001
            gold_error = str(exc)

        successful_sql = [attempt for attempt in sql_attempts if attempt.get("ok")]
        final_sql = successful_sql[-1] if successful_sql else None
        predicted_headers = list(final_sql.get("headers", [])) if final_sql else []
        predicted_rows = [tuple(row) for row in final_sql.get("rows", [])] if final_sql else []

        match_headers = headers_match(predicted_headers, gold_headers)
        is_exact_match = exact_match(predicted_headers, predicted_rows, gold_headers, gold_rows) if final_sql else False
        is_unordered_match = (
            unordered_match(predicted_headers, predicted_rows, gold_headers, gold_rows) if final_sql else False
        )
        is_scalar_text_match = scalar_text_match(agent_answer, gold_rows)
        passed = bool(is_exact_match or is_unordered_match or is_scalar_text_match)

        try:
            return BenchmarkQuestionResult(
                item_id=item.item_id,
                question=item.question,
                category=item.category,
                difficulty=item.difficulty,
                gold_sql=item.gold_sql,
                gold_headers=gold_headers,
                gold_rows=[_safe_jsonable(list(row)) for row in gold_rows],
                gold_error=gold_error,
                agent_answer=agent_answer,
                agent_error=agent_error,
                duration_ms=duration_ms,
                sql_attempt_count=len(sql_attempts),
                successful_sql_attempt_count=len(successful_sql),
                final_sql=final_sql.get("sql") if final_sql else None,
                final_sql_headers=predicted_headers,
                final_sql_rows=[_safe_jsonable(list(row)) for row in predicted_rows],
                headers_match=match_headers,
                exact_match=is_exact_match,
                unordered_match=is_unordered_match,
                scalar_text_match=is_scalar_text_match,
                passed=passed,
                sql_attempts=sql_attempts,
                token_usage=token_usage,
                agent_state=agent_state,
                step_count=step_count,
            )
        finally:
            if dispose_engine:
                local_engine.dispose()

    def run_single(
        self,
        question: str,
        expected_sql: str,
        *,
        item_id: str = "interactive",
        category: str = "interactive",
        difficulty: str = "interactive",
    ) -> BenchmarkQuestionResult:
        item = EvalItem(
            item_id=item_id,
            question=question,
            gold_sql=expected_sql,
            category=category,
            difficulty=difficulty,
        )
        return self._evaluate_item(item)

    def run(self, max_items: int | None = None):
        load_dotenv(".env", override=True)
        items = load_dataset(self.dataset_path)
        if max_items is not None:
            items = items[:max_items]

        existing_results = self._load_existing_results()
        self._write_manifest(total_items=len(items), completed_items=len(existing_results))

        remaining_items = [item for item in items if item.item_id not in existing_results]

        if remaining_items:
            if self.max_workers == 1:
                runtime = build_agent_runtime(self.agent_config)
                engine = create_engine(self.agent_config.database_url)
                try:
                    for item in remaining_items:
                        result = self._evaluate_item(item, runtime=runtime, engine=engine)
                        existing_results[result.item_id] = result
                        self._persist_question_result(result)
                        self._write_manifest(total_items=len(items), completed_items=len(existing_results))
                finally:
                    engine.dispose()
            else:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_map = {executor.submit(self._evaluate_item, item): item for item in remaining_items}
                    for future in as_completed(future_map):
                        result = future.result()
                        existing_results[result.item_id] = result
                        self._persist_question_result(result)
                        self._write_manifest(total_items=len(items), completed_items=len(existing_results))

        ordered_results = [existing_results[item.item_id] for item in items if item.item_id in existing_results]
        summary = summarize_results(ordered_results)
        summary.update(
            {
                "run_id": self.run_id,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "dataset_path": str(self.dataset_path),
                "config_hash": self.config_hash,
                "config_label": self.config_label,
                "run_dir": str(self.run_dir),
            }
        )

        benchmark_result = build_result(
            run_id=self.run_id,
            dataset_path=str(self.dataset_path),
            config_hash=self.config_hash,
            config_label=self.config_label,
            run_dir=str(self.run_dir),
            summary=summary,
            results=ordered_results,
            settings=_settings_snapshot(self.agent_config),
        )
        ReportGenerator(benchmark_result).write_run_artifacts(self.run_dir)
        return benchmark_result
