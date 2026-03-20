from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from .pipeline import build_dataset
from .unified_review import UnifiedReviewRepository


def merge_answer_fields_into_exam(
    current_exam: dict[str, Any],
    rebuilt_exam: dict[str, Any],
) -> tuple[dict[str, Any], list[int]]:
    updated_exam = copy.deepcopy(current_exam)
    rebuilt_questions = {int(question["number"]): question for question in rebuilt_exam.get("questions", [])}
    changed_questions: list[int] = []

    for question in updated_exam.get("questions", []):
        question_number = int(question["number"])
        rebuilt_question = rebuilt_questions[question_number]
        rebuilt_answer = rebuilt_question.get("answer")
        if question.get("answer") != rebuilt_answer:
            changed_questions.append(question_number)
        question["answer"] = rebuilt_answer

    updated_exam["answer_key"] = dict(rebuilt_exam.get("answer_key", {}))
    return updated_exam, changed_questions


def merge_answer_fields_into_audit(
    current_audit: dict[str, Any],
    rebuilt_audit: dict[str, Any],
) -> dict[str, Any]:
    updated_audit = copy.deepcopy(current_audit)
    rebuilt_questions = {int(question["number"]): question for question in rebuilt_audit.get("questions", [])}

    updated_audit["answer_source"] = copy.deepcopy(rebuilt_audit.get("answer_source", {}))
    for question in updated_audit.get("questions", []):
        question_number = int(question["number"])
        rebuilt_question = rebuilt_questions[question_number]
        question["answer"] = rebuilt_question.get("answer")
        question["answer_confidence"] = rebuilt_question.get("answer_confidence")

    return updated_audit


def merge_answer_key_into_release(
    current_release_exam: dict[str, Any],
    rebuilt_exam: dict[str, Any],
) -> dict[str, Any]:
    updated_release_exam = copy.deepcopy(current_release_exam)
    updated_release_exam["answer_key"] = dict(rebuilt_exam.get("answer_key", {}))
    return updated_release_exam


def reset_changed_answer_fields(
    review_payload: dict[str, Any],
    replacement_fields: list[dict[str, Any]],
    changed_questions: list[int],
) -> tuple[dict[str, Any], list[str]]:
    if not changed_questions:
        return copy.deepcopy(review_payload), []

    changed_set = set(changed_questions)
    replacement_by_id = {str(field["field_id"]): copy.deepcopy(field) for field in replacement_fields}
    updated_review = copy.deepcopy(review_payload)
    updated_fields: list[dict[str, Any]] = []
    replaced_field_ids: list[str] = []

    for field in updated_review.get("fields", []):
        if field.get("kind") == "answer" and int(field.get("question_number", 0)) in changed_set:
            field_id = str(field.get("field_id", ""))
            replacement = replacement_by_id.get(field_id)
            if replacement:
                updated_fields.append(replacement)
                replaced_field_ids.append(field_id)
                continue
        updated_fields.append(field)

    updated_review["fields"] = updated_fields
    updated_review["field_count"] = len(updated_fields)
    return updated_review, replaced_field_ids


def sync_rebuilt_answers(
    rebuilt_data_dir: Path | str,
    data_dir: Path | str | None,
    release_dir: Path | str,
    *,
    review_dir: Path | str | None = None,
    exam_ids: list[str] | None = None,
    dry_run: bool = False,
    answer_field_provider: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    rebuilt_data_path = Path(rebuilt_data_dir).resolve()
    data_path = Path(data_dir).resolve() if data_dir is not None else None
    release_path = Path(release_dir).resolve()
    review_path = Path(review_dir).resolve() if review_dir else None
    if review_path is not None and data_path is None:
        raise ValueError("review_dir requires data_dir so answer fields can be synchronized against a working dataset.")

    manifest = _read_json(rebuilt_data_path / "manifest.json")
    selected_exam_ids = exam_ids or [entry["exam_id"] for entry in manifest.get("exams", [])]
    repository = (
        UnifiedReviewRepository(data_dir=data_path, review_dir=review_path)
        if review_path is not None and data_path is not None and answer_field_provider is None
        else None
    )

    if data_path is not None and not dry_run:
        _write_manifest_if_missing(data_path / "manifest.json", manifest)

    exam_summaries: list[dict[str, Any]] = []
    for exam_id in selected_exam_ids:
        rebuilt_exam_path = rebuilt_data_path / "exams" / exam_id / "exam.json"
        rebuilt_audit_path = rebuilt_data_path / "exams" / exam_id / "audit.json"

        rebuilt_exam = _read_json(rebuilt_exam_path)
        rebuilt_audit = _read_json(rebuilt_audit_path)

        exam_updated = False
        audit_updated = False
        changed_questions: list[int] = []
        updated_exam = copy.deepcopy(rebuilt_exam)
        if data_path is not None:
            current_exam_path = data_path / "exams" / exam_id / "exam.json"
            if current_exam_path.exists():
                current_exam = _read_json(current_exam_path)
                updated_exam, changed_questions = merge_answer_fields_into_exam(current_exam, rebuilt_exam)
                exam_updated = updated_exam != current_exam
            else:
                updated_exam = copy.deepcopy(rebuilt_exam)
                changed_questions = [int(question["number"]) for question in rebuilt_exam.get("questions", [])]
                exam_updated = True
            if exam_updated and not dry_run:
                _write_json(current_exam_path, updated_exam)

            current_audit_path = data_path / "exams" / exam_id / "audit.json"
            if current_audit_path.exists():
                current_audit = _read_json(current_audit_path)
                updated_audit = merge_answer_fields_into_audit(current_audit, rebuilt_audit)
                audit_updated = updated_audit != current_audit
            else:
                updated_audit = copy.deepcopy(rebuilt_audit)
                audit_updated = True
            if audit_updated and not dry_run:
                _write_json(current_audit_path, updated_audit)

        release_exam_path = release_path / "exams" / exam_id / "exam.json"
        release_updated = False
        if release_exam_path.exists():
            current_release_exam = _read_json(release_exam_path)
            updated_release_exam = merge_answer_key_into_release(current_release_exam, rebuilt_exam)
            release_updated = updated_release_exam != current_release_exam
            if release_updated and not dry_run:
                _write_json(release_exam_path, updated_release_exam)

        review_field_ids: list[str] = []
        if review_path is not None and data_path is not None:
            review_file_path = review_path / f"{exam_id}.json"
            if review_file_path.exists():
                review_payload = _read_json(review_file_path)
                if any(field.get("kind") == "answer" for field in review_payload.get("fields", [])):
                    replacement_fields = (
                        answer_field_provider(updated_exam)
                        if answer_field_provider is not None
                        else repository.answer_fields(updated_exam)
                    )
                    updated_review, review_field_ids = reset_changed_answer_fields(
                        review_payload,
                        replacement_fields,
                        changed_questions,
                    )
                    if review_field_ids and not dry_run:
                        _write_json(review_file_path, updated_review)

        exam_summaries.append(
            {
                "exam_id": exam_id,
                "changed_questions": changed_questions,
                "exam_updated": exam_updated,
                "audit_updated": audit_updated,
                "release_updated": release_updated,
                "review_field_ids_reset": review_field_ids,
            }
        )

    return {
        "rebuilt_data_dir": rebuilt_data_path.as_posix(),
        "data_dir": data_path.as_posix() if data_path else None,
        "release_dir": release_path.as_posix(),
        "review_dir": review_path.as_posix() if review_path else None,
        "dry_run": dry_run,
        "exam_count": len(exam_summaries),
        "exams": exam_summaries,
    }


def rebuild_and_sync_answers(
    source_dir: Path | str,
    data_dir: Path | str | None,
    release_dir: Path | str,
    *,
    review_dir: Path | str | None = None,
    exam_ids: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_path = Path(source_dir).resolve()
    with tempfile.TemporaryDirectory(prefix="kangaroo-answer-rebuild-") as temp_dir:
        rebuilt_data_dir = Path(temp_dir) / "data"
        manifest = build_dataset(source_path, rebuilt_data_dir)
        summary = sync_rebuilt_answers(
            rebuilt_data_dir=rebuilt_data_dir,
            data_dir=data_dir,
            release_dir=release_dir,
            review_dir=review_dir,
            exam_ids=exam_ids,
            dry_run=dry_run,
        )
        summary["rebuild_manifest_generated_at"] = manifest.get("generated_at")
        return summary


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_manifest_if_missing(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        return
    _write_json(path, payload)
