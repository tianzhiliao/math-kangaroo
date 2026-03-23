#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.pipeline import build_exam_id, classify_documents
from kangaroo_pdf.workspace_paths import workspace_paths


REMAINING_EXAM_IDS = [
    "canada-gr0102e-2020",
    "canada-gr0102e-2021",
    "felix-brazil-2020",
    "felix-brazil-2021",
    "felix-austria-2014",
    "felix-austria-2015",
    "felix-austria-2016",
    "felix-austria-2017",
    "felix-austria-2018",
    "felix-austria-2019",
    "felix-austria-2024",
    "felix-austria-2025",
]

QA_GATE_ARGS = [
    "--qa-gate",
    "--max-high-risk",
    "0",
    "--max-option-alignment-conflict",
    "0",
    "--max-illegal-char-ratio",
    "0.0",
]


@dataclass(frozen=True)
class ExamTask:
    exam_id: str
    source_pdf: Path
    answer_pdf: Path | None
    year: int | None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_command(command: list[str], cwd: Path) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        cwd=cwd.as_posix(),
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _build_task_index(source_dir: Path) -> dict[str, ExamTask]:
    documents = classify_documents(source_dir)
    answer_by_year = {
        document.year: Path(document.path)
        for document in documents
        if document.is_answer_table
    }

    task_by_exam_id: dict[str, ExamTask] = {}
    for document in documents:
        if document.is_answer_table:
            continue
        exam_id = build_exam_id(document)
        task_by_exam_id[exam_id] = ExamTask(
            exam_id=exam_id,
            source_pdf=Path(document.path),
            answer_pdf=answer_by_year.get(document.year),
            year=document.year,
        )
    return task_by_exam_id


def _categorize_failure(result: dict[str, Any]) -> str:
    steps = result.get("steps", {})
    text_only = steps.get("text_only", {})
    full_extract = steps.get("full_extract", {})

    if text_only.get("return_code", 0) != 0:
        if text_only.get("return_code") == 2:
            return "qa_gate"
        return "parser_error"
    if full_extract.get("return_code", 0) != 0:
        return "parser_error"
    if result.get("missing_paths"):
        return "missing_file"
    return "unknown"


def _run_single_exam_task(
    task: ExamTask,
    *,
    root: Path,
    text_only_dir: Path,
    full_extract_root: Path,
    child_results_dir: Path,
) -> dict[str, Any]:
    exam_id = task.exam_id
    started_at = datetime.now(timezone.utc)

    text_json = text_only_dir / f"{exam_id}.text-only.json"
    review_html = text_only_dir / f"{exam_id}.review.html"
    full_exam_root = full_extract_root / exam_id
    full_data_dir = full_exam_root / "data"
    full_exam_json = full_data_dir / "exams" / exam_id / "exam.json"
    child_result_path = child_results_dir / f"{exam_id}.result.json"

    text_cmd = [
        sys.executable,
        str(root / "scripts" / "extract_text_only_exam.py"),
        "--pdf",
        str(task.source_pdf),
        "--output-json",
        str(text_json),
        *QA_GATE_ARGS,
    ]
    text_rc, text_stdout, text_stderr = _run_command(text_cmd, root)

    review_rc = 0
    review_stdout = ""
    review_stderr = ""
    if text_rc == 0:
        review_cmd = [
            sys.executable,
            str(root / "scripts" / "render_text_only_review.py"),
            "--json",
            str(text_json),
            "--output-html",
            str(review_html),
        ]
        review_rc, review_stdout, review_stderr = _run_command(review_cmd, root)

    full_cmd = [
        sys.executable,
        str(root / "scripts" / "build_exam_data.py"),
        "--source-dir",
        str(task.source_pdf.parent),
        "--output-dir",
        str(full_data_dir),
        "--exam-id",
        exam_id,
    ]
    full_rc, full_stdout, full_stderr = _run_command(full_cmd, root)

    text_blocking_errors: list[str] = []
    text_quality: dict[str, Any] = {}
    if text_json.exists():
        payload = _read_json(text_json)
        text_blocking_errors = list(payload.get("blocking_errors", []))
        text_quality = dict(payload.get("quality_summary", {}))

    missing_paths = [
        str(path)
        for path in (text_json, review_html, full_exam_json)
        if not path.exists()
    ]
    passed = (
        text_rc == 0
        and review_rc == 0
        and full_rc == 0
        and not text_blocking_errors
        and not missing_paths
    )

    result: dict[str, Any] = {
        "exam_id": exam_id,
        "year": task.year,
        "passed": passed,
        "failure_category": "" if passed else "unknown",
        "source_pdf": str(task.source_pdf),
        "answer_pdf": str(task.answer_pdf) if task.answer_pdf else "",
        "artifacts": {
            "text_only_json": str(text_json),
            "review_html": str(review_html),
            "full_exam_json": str(full_exam_json),
        },
        "blocking_errors": text_blocking_errors,
        "quality_summary": text_quality,
        "missing_paths": missing_paths,
        "steps": {
            "text_only": {
                "command": text_cmd,
                "return_code": text_rc,
                "stdout": text_stdout,
                "stderr": text_stderr,
            },
            "render_review": {
                "return_code": review_rc,
                "stdout": review_stdout,
                "stderr": review_stderr,
            },
            "full_extract": {
                "command": full_cmd,
                "return_code": full_rc,
                "stdout": full_stdout,
                "stderr": full_stderr,
            },
        },
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    if not passed:
        result["failure_category"] = _categorize_failure(result)

    _write_json(child_result_path, result)
    return result


def _run_wave(
    tasks: list[ExamTask],
    *,
    root: Path,
    workers: int,
    text_only_dir: Path,
    full_extract_root: Path,
    child_results_dir: Path,
) -> list[dict[str, Any]]:
    if not tasks:
        return []
    results: list[dict[str, Any]] = []
    max_workers = max(1, min(workers, len(tasks)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _run_single_exam_task,
                task,
                root=root,
                text_only_dir=text_only_dir,
                full_extract_root=full_extract_root,
                child_results_dir=child_results_dir,
            )
            for task in tasks
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: item["exam_id"])


def _chunk(items: list[ExamTask], wave_size: int) -> list[list[ExamTask]]:
    return [items[index : index + wave_size] for index in range(0, len(items), wave_size)]


def _summarize(
    *,
    all_results: list[dict[str, Any]],
    selected_exam_ids: list[str],
    workers: int,
    wave_size: int,
    retries: int,
    text_only_dir: Path,
    full_extract_root: Path,
    child_results_dir: Path,
) -> dict[str, Any]:
    passed_exam_ids = sorted(result["exam_id"] for result in all_results if result["passed"])
    failed_results = [result for result in all_results if not result["passed"]]
    failed_exam_ids = sorted(result["exam_id"] for result in failed_results)

    failure_reason_counts: dict[str, int] = {}
    for result in failed_results:
        key = result.get("failure_category", "unknown")
        failure_reason_counts[key] = failure_reason_counts.get(key, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selected_exam_ids": selected_exam_ids,
        "run_config": {
            "workers": workers,
            "wave_size": wave_size,
            "retries": retries,
            "qa_gate": {
                "max_high_risk": 0,
                "max_option_alignment_conflict": 0,
                "max_illegal_char_ratio": 0.0,
            },
        },
        "paths": {
            "text_only_dir": str(text_only_dir),
            "full_extract_root": str(full_extract_root),
            "child_results_dir": str(child_results_dir),
        },
        "total_count": len(selected_exam_ids),
        "passed_count": len(passed_exam_ids),
        "failed_count": len(failed_exam_ids),
        "passed_exam_ids": passed_exam_ids,
        "failed_exam_ids": failed_exam_ids,
        "retry_candidates": failed_exam_ids,
        "failure_reason_counts": failure_reason_counts,
        "results": all_results,
    }


def main() -> None:
    paths = workspace_paths(ROOT)
    parser = argparse.ArgumentParser(description="Parallel re-extract remaining exam PDFs with per-exam child results.")
    parser.add_argument("--source-dir", default=str(paths.source_dir))
    parser.add_argument("--generated-root", default=str(paths.generated_root))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--wave-size", type=int, default=4)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument(
        "--exam-id",
        dest="exam_ids",
        action="append",
        help="Optional subset of exam_id values. Can be repeated.",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    generated_root = Path(args.generated_root).resolve()
    generated_root.mkdir(parents=True, exist_ok=True)

    text_only_dir = generated_root / "text-only"
    full_extract_root = generated_root / "reextract" / "full-data"
    child_results_dir = generated_root / "reextract" / "child-results"
    batch_summary_path = generated_root / "reextract" / "batch_summary.json"
    text_only_dir.mkdir(parents=True, exist_ok=True)
    full_extract_root.mkdir(parents=True, exist_ok=True)
    child_results_dir.mkdir(parents=True, exist_ok=True)

    task_index = _build_task_index(source_dir)
    selected_exam_ids = args.exam_ids or REMAINING_EXAM_IDS
    unknown_exam_ids = sorted(set(selected_exam_ids) - set(task_index))
    if unknown_exam_ids:
        unknown_csv = ", ".join(unknown_exam_ids)
        raise SystemExit(f"Unknown exam_id values: {unknown_csv}")

    tasks = [task_index[exam_id] for exam_id in selected_exam_ids]
    all_results_by_exam: dict[str, dict[str, Any]] = {}
    pending_tasks = tasks
    remaining_retries = max(0, args.retries)

    while True:
        waves = _chunk(pending_tasks, max(1, args.wave_size))
        for wave in waves:
            wave_results = _run_wave(
                wave,
                root=ROOT,
                workers=max(1, args.workers),
                text_only_dir=text_only_dir,
                full_extract_root=full_extract_root,
                child_results_dir=child_results_dir,
            )
            for result in wave_results:
                all_results_by_exam[result["exam_id"]] = result

        failed_exam_ids = [
            exam_id
            for exam_id in selected_exam_ids
            if not all_results_by_exam.get(exam_id, {}).get("passed", False)
        ]
        if not failed_exam_ids or remaining_retries <= 0:
            break
        pending_tasks = [task_index[exam_id] for exam_id in failed_exam_ids]
        remaining_retries -= 1

    ordered_results = [all_results_by_exam[exam_id] for exam_id in selected_exam_ids]
    summary = _summarize(
        all_results=ordered_results,
        selected_exam_ids=selected_exam_ids,
        workers=max(1, args.workers),
        wave_size=max(1, args.wave_size),
        retries=max(0, args.retries),
        text_only_dir=text_only_dir,
        full_extract_root=full_extract_root,
        child_results_dir=child_results_dir,
    )
    _write_json(batch_summary_path, summary)
    print(json.dumps({"batch_summary": str(batch_summary_path), **summary}, ensure_ascii=False, indent=2))
    if summary["failed_count"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
