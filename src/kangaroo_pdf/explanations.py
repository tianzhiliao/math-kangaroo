from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

EXPLANATION_SCHEMA_VERSION = 1
ORIGINAL_EXPLANATIONS_FILENAME = "explanations.json"
VARIANT_EXPLANATION_FILENAME = "explanation.json"
REVIEW_STATUSES = {"unreviewed", "flagged", "approved"}
CHOICE_LABEL_PATTERN = re.compile(r"^[A-E]$")

ENTRY_KEYS = {
    "source",
    "content_hash",
    "answer",
    "independent_answer",
    "key_idea",
    "steps",
    "answer_sentence",
    "choice_feedback",
    "generated_by",
    "generated_at",
    "review",
}
ORIGINAL_FILE_KEYS = {"schema_version", "prompt_version", "questions"}
VARIANT_FILE_KEYS = ENTRY_KEYS | {"schema_version", "prompt_version"}
REVIEW_KEYS = {"status", "note"}

# The letter group is case-sensitive so "the answer is a bird" is not read as a claim for A,
# and "is right of" / "is right next to" describe a position, not a claim.
_IS_CORRECT = r"(?i:is\s+(?:correct|right))\b(?!\s+(?i:of|next|beside|above|below)\b)"
ANSWER_CLAIM_PATTERNS = (
    re.compile(r"(?i:\banswer\s+is)\s+([A-E])\b"),
    re.compile(r"(?i:\boption)\s+([A-E])\s+" + _IS_CORRECT),
    re.compile(r"\b([A-E])\s+" + _IS_CORRECT),
)


@dataclass(frozen=True)
class QuestionRef:
    exam_id: str
    question_id: str
    source: str
    question: dict[str, Any]
    answer: str
    asset_files: dict[str, Path]

    @property
    def key(self) -> str:
        return f"{self.exam_id}/{self.source}/{self.question_id}"


def question_content_hash(ref: QuestionRef) -> str:
    """Hash everything an explanation depends on: text, choices, answer, and figure bytes."""
    question = ref.question
    asset_ids = list(question.get("shared_asset_refs", []))
    for choice in question.get("choices", []):
        asset_ids.extend(choice.get("asset_refs", []))
    payload = {
        "stem_text": question.get("stem_text", ""),
        "choices": [
            {
                "label": choice.get("label"),
                "text": choice.get("text", ""),
                "asset_refs": list(choice.get("asset_refs", [])),
            }
            for choice in question.get("choices", [])
        ],
        "shared_asset_refs": list(question.get("shared_asset_refs", [])),
        "answer": ref.answer,
        "assets": {asset_id: _file_sha256(ref.asset_files.get(asset_id)) for asset_id in sorted(set(asset_ids))},
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def load_original_questions(release_dir: Path, exam_id: str) -> list[QuestionRef]:
    exam_dir = release_dir / "exams" / exam_id
    exam = _read_json(exam_dir / "exam.json")
    asset_files = {asset["id"]: exam_dir / asset["path"] for asset in exam.get("assets", [])}
    answer_key = exam.get("answer_key", {})
    return [
        QuestionRef(
            exam_id=exam_id,
            question_id=question["id"],
            source="original",
            question=question,
            answer=str(answer_key.get(str(question["number"]), "")),
            asset_files=asset_files,
        )
        for question in exam.get("questions", [])
    ]


def load_variant_questions(generated_dir: Path, exam_id: str) -> list[QuestionRef]:
    exam_dir = generated_dir / exam_id
    manifest_path = exam_dir / "manifest.json"
    if not manifest_path.exists():
        return []
    refs: list[QuestionRef] = []
    for item in _read_json(manifest_path).get("questions", []):
        if item.get("status") != "generated":
            continue
        question_dir = exam_dir / item["id"]
        question = _read_json(question_dir / "question.json")
        refs.append(
            QuestionRef(
                exam_id=exam_id,
                question_id=item["id"],
                source="variant",
                question=question,
                answer=str(question.get("answer", "")),
                asset_files={asset["id"]: question_dir / asset["path"] for asset in question.get("assets", [])},
            )
        )
    return refs


def original_explanations_path(release_dir: Path, exam_id: str) -> Path:
    return release_dir / "exams" / exam_id / ORIGINAL_EXPLANATIONS_FILENAME


def variant_explanation_path(generated_dir: Path, exam_id: str, question_id: str) -> Path:
    return generated_dir / exam_id / question_id / VARIANT_EXPLANATION_FILENAME


def exams_with_explanations(release_dir: Path, generated_dir: Path) -> list[str]:
    exam_ids = {path.parent.name for path in (release_dir / "exams").glob(f"*/{ORIGINAL_EXPLANATIONS_FILENAME}")}
    exam_ids.update(path.parent.parent.name for path in generated_dir.glob(f"*/*/{VARIANT_EXPLANATION_FILENAME}"))
    return sorted(exam_ids)


def validate_entry(ref: QuestionRef, entry: Any) -> list[str]:
    """Return every rule this explanation entry breaks for its question."""
    if not isinstance(entry, dict):
        return ["entry must be an object"]
    errors: list[str] = []
    missing = ENTRY_KEYS - entry.keys()
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")
        return errors

    if entry["source"] != ref.source:
        errors.append(f"source must be {ref.source!r}, got {entry['source']!r}")
    if entry["content_hash"] != question_content_hash(ref):
        errors.append("content_hash does not match the current question; the explanation is stale")
    if entry["answer"] != ref.answer:
        errors.append(f"answer {entry['answer']!r} does not match the answer key {ref.answer!r}")

    review = entry["review"]
    if not isinstance(review, dict) or set(review) != REVIEW_KEYS:
        errors.append(f"review must have exactly the keys {sorted(REVIEW_KEYS)}")
        review = {"status": None, "note": None}
    elif review["status"] not in REVIEW_STATUSES:
        errors.append(f"review.status must be one of {sorted(REVIEW_STATUSES)}")
    elif review["status"] == "flagged" and not _non_empty_string(review["note"]):
        errors.append("a flagged entry needs a review.note saying what to check")

    # null means the solver could not reach an answer without the key; that also needs a human.
    independent = entry["independent_answer"]
    if independent is not None and (not isinstance(independent, str) or not CHOICE_LABEL_PATTERN.match(independent)):
        errors.append("independent_answer must be a single letter A-E or null")
    elif independent != ref.answer and review["status"] not in {"flagged", "approved"}:
        errors.append(
            f"independent_answer {independent} disagrees with the key {ref.answer}; "
            "set review.status to flagged (or approved after a human check)"
        )

    if not _non_empty_string(entry["key_idea"]):
        errors.append("key_idea must be a non-empty string")
    steps = entry["steps"]
    if not isinstance(steps, list) or len(steps) < 2 or not all(_non_empty_string(step) for step in steps):
        errors.append("steps must be a list of at least two non-empty strings")
        steps = []
    expected_sentence = f"So the answer is {ref.answer}."
    if entry["answer_sentence"] != expected_sentence:
        errors.append(f"answer_sentence must be exactly {expected_sentence!r}")

    feedback = entry["choice_feedback"]
    wrong_labels = {choice["label"] for choice in ref.question.get("choices", [])} - {ref.answer}
    if not isinstance(feedback, dict):
        errors.append("choice_feedback must be an object keyed by wrong choice labels")
        feedback = {}
    else:
        if set(feedback) != wrong_labels:
            errors.append(f"choice_feedback must cover exactly the wrong choices {sorted(wrong_labels)}, got {sorted(feedback)}")
        if not all(_non_empty_string(text) for text in feedback.values()):
            errors.append("choice_feedback values must be non-empty strings")

    texts = [entry["key_idea"], entry["answer_sentence"], *steps, *feedback.values()]
    claims = sorted({label for text in texts if isinstance(text, str) for label in _answer_claims(text)})
    wrong_claims = [label for label in claims if label != ref.answer]
    if wrong_claims:
        errors.append(f"text claims a wrong answer: {wrong_claims}")

    if not _non_empty_string(entry["generated_by"]):
        errors.append("generated_by must be a non-empty string")
    if not _is_iso_timestamp(entry["generated_at"]):
        errors.append("generated_at must be an ISO 8601 timestamp")
    return errors


def validate_exam(release_dir: Path, generated_dir: Path, exam_id: str) -> dict[str, Any]:
    """Check one exam's original and variant explanations; missing explanations count as errors."""
    errors: dict[str, list[str]] = {}
    flagged: list[str] = []
    checked = 0

    originals = load_original_questions(release_dir, exam_id)
    original_path = original_explanations_path(release_dir, exam_id)
    original_entries: dict[str, Any] = {}
    if not original_path.exists():
        errors[f"{exam_id}/original"] = [f"missing {original_path.name}"]
    else:
        payload = _read_json(original_path)
        file_errors = _validate_file_header(payload, ORIGINAL_FILE_KEYS)
        if not isinstance(payload.get("questions"), dict):
            file_errors.append("questions must be an object keyed by question id")
        else:
            original_entries = payload["questions"]
            unknown = sorted(set(original_entries) - {ref.question_id for ref in originals})
            if unknown:
                file_errors.append(f"entries for unknown questions: {unknown}")
        if file_errors:
            errors[f"{exam_id}/original"] = file_errors

    for ref in originals:
        if not original_path.exists():
            continue
        checked += 1
        if ref.question_id not in original_entries:
            errors[ref.key] = ["missing explanation"]
            continue
        _record(ref, original_entries[ref.question_id], errors, flagged)

    for ref in load_variant_questions(generated_dir, exam_id):
        checked += 1
        path = variant_explanation_path(generated_dir, exam_id, ref.question_id)
        if not path.exists():
            errors[ref.key] = [f"missing {path.name}"]
            continue
        payload = _read_json(path)
        file_errors = _validate_file_header(payload, VARIANT_FILE_KEYS)
        if file_errors:
            errors[ref.key] = file_errors
            continue
        _record(ref, payload, errors, flagged)

    return {"exam_id": exam_id, "checked": checked, "errors": errors, "flagged": flagged}


def stamp_content_hashes(release_dir: Path, generated_dir: Path, exam_id: str) -> list[str]:
    """Fill in empty content_hash fields. Existing hashes are never overwritten."""
    stamped: list[str] = []
    original_path = original_explanations_path(release_dir, exam_id)
    if original_path.exists():
        payload = _read_json(original_path)
        entries = payload.get("questions", {})
        changed = False
        for ref in load_original_questions(release_dir, exam_id):
            entry = entries.get(ref.question_id)
            if isinstance(entry, dict) and not entry.get("content_hash"):
                entry["content_hash"] = question_content_hash(ref)
                stamped.append(ref.key)
                changed = True
        if changed:
            _write_json(original_path, payload)

    for ref in load_variant_questions(generated_dir, exam_id):
        path = variant_explanation_path(generated_dir, exam_id, ref.question_id)
        if not path.exists():
            continue
        payload = _read_json(path)
        if not payload.get("content_hash"):
            payload["content_hash"] = question_content_hash(ref)
            _write_json(path, payload)
            stamped.append(ref.key)
    return stamped


def _record(ref: QuestionRef, entry: Any, errors: dict[str, list[str]], flagged: list[str]) -> None:
    entry_errors = validate_entry(ref, entry)
    if entry_errors:
        errors[ref.key] = entry_errors
    elif entry["review"]["status"] == "flagged":
        flagged.append(f"{ref.key}: {entry['review']['note']}")


def _validate_file_header(payload: Any, expected_keys: set[str]) -> list[str]:
    if not isinstance(payload, dict):
        return ["file must contain a JSON object"]
    errors: list[str] = []
    if set(payload) != expected_keys:
        errors.append(f"file keys must be {sorted(expected_keys)}, got {sorted(payload)}")
    if payload.get("schema_version") != EXPLANATION_SCHEMA_VERSION:
        errors.append(f"schema_version must be {EXPLANATION_SCHEMA_VERSION}")
    if not _non_empty_string(payload.get("prompt_version")):
        errors.append("prompt_version must be a non-empty string")
    return errors


def _answer_claims(text: str) -> set[str]:
    return {match.group(1) for pattern in ANSWER_CLAIM_PATTERNS for match in pattern.finditer(text)}


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
