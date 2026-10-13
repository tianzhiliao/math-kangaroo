from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .config import get_settings


@dataclass(frozen=True)
class QuestionAsset:
    id: str
    label: str
    role: str
    media_type: str
    data_url: str


@dataclass(frozen=True)
class QuestionSnapshot:
    exam_id: str
    year: int
    level: str
    language: str
    question_number: int
    stem_text: str
    correct_label: str
    choices: list[dict[str, Any]]
    stem_assets: list[QuestionAsset]
    choice_assets: dict[str, list[QuestionAsset]]
    # Set for AI-generated similar questions: a digest of question.json so a
    # regenerated variant never reuses an old cached explanation.
    variant_digest: str | None = None


QUESTION_ID_PATTERN = re.compile(r"^q\d{2}$")
EXAM_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def release_root() -> Path:
    return get_settings().release_data_path


def load_manifest() -> dict[str, Any]:
    path = release_root() / "manifest.json"
    if not path.is_file():
        raise HTTPException(status_code=500, detail="manifest_not_found")
    return json.loads(path.read_text(encoding="utf-8"))


def load_exam(exam_id: str) -> dict[str, Any]:
    path = release_root() / "exams" / exam_id / "exam.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="exam_not_found")
    return json.loads(path.read_text(encoding="utf-8"))


def load_question_stem_text(exam_id: str, question_number: int, *, variant: bool = False) -> str:
    if variant:
        return str(_load_variant(exam_id, question_number)[1].get("stem_text", ""))
    question = _find_question(load_exam(exam_id), question_number)
    return str(question.get("stem_text", ""))


def generated_root() -> Path:
    return get_settings().generated_questions_path


def resolve_variant_dir(exam_id: str, question_id: str) -> Path | None:
    """Folder of the generated similar question, following skipped duplicates.

    A variant marked ``withdrawn`` in its manifest is treated as missing.
    """
    if not EXAM_ID_PATTERN.match(exam_id) or not QUESTION_ID_PATTERN.match(question_id):
        return None
    root = generated_root()
    entry = _variant_manifest_entry(root, exam_id, question_id)
    if entry and entry.get("status") == "withdrawn":
        return None
    direct = root / exam_id / question_id
    if (direct / "question.json").is_file():
        return direct
    if not entry or entry.get("status") != "skipped-duplicate":
        return None
    dup_exam = entry.get("duplicate_of")
    dup_question = entry.get("duplicate_question")
    if not isinstance(dup_exam, str) or not isinstance(dup_question, str):
        return None
    if not EXAM_ID_PATTERN.match(dup_exam) or not QUESTION_ID_PATTERN.match(dup_question):
        return None
    target_entry = _variant_manifest_entry(root, dup_exam, dup_question)
    if target_entry and target_entry.get("status") == "withdrawn":
        return None
    target = root / dup_exam / dup_question
    return target if (target / "question.json").is_file() else None


def _variant_manifest_entry(root: Path, exam_id: str, question_id: str) -> dict[str, Any] | None:
    manifest_path = root / exam_id / "manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return next((q for q in manifest.get("questions", []) if q.get("id") == question_id), None)


def load_variant_snapshot(exam_id: str, question_number: int) -> QuestionSnapshot:
    """Snapshot of the AI-generated similar question for a source question.

    The variant's figures are SVG, which the vision model does not accept, so
    the model gets ``card.png``: the rendered question with stem, figure and
    choices in one image.
    """
    exam, question, folder, raw = _load_variant_with_folder(exam_id, question_number)
    choices = [
        {"label": str(choice["label"]), "text": str(choice.get("text", ""))}
        for choice in question.get("choices", [])
    ]
    choice_labels = {choice["label"] for choice in choices}
    correct_label = str(question.get("answer", "")).strip().upper()
    if not correct_label or correct_label not in choice_labels:
        raise HTTPException(status_code=500, detail="invalid_variant_answer")

    stem_assets: list[QuestionAsset] = []
    card = folder / "card.png"
    if card.is_file():
        encoded = base64.b64encode(card.read_bytes()).decode("ascii")
        stem_assets.append(
            QuestionAsset(
                id="card",
                label="Question card image (stem, picture and choices)",
                role="card",
                media_type="image/png",
                data_url=f"data:image/png;base64,{encoded}",
            )
        )
    return QuestionSnapshot(
        exam_id=exam_id,
        year=int(exam["year"]),
        level=str(exam["level"]),
        language=str(exam["language"]),
        question_number=question_number,
        stem_text=str(question.get("stem_text", "")),
        correct_label=correct_label,
        choices=choices,
        stem_assets=stem_assets,
        choice_assets={choice["label"]: [] for choice in choices},
        variant_digest=hashlib.sha256(raw).hexdigest()[:16],
    )


def _load_variant(exam_id: str, question_number: int) -> tuple[dict[str, Any], dict[str, Any]]:
    exam, question, _, _ = _load_variant_with_folder(exam_id, question_number)
    return exam, question


def _load_variant_with_folder(
    exam_id: str, question_number: int
) -> tuple[dict[str, Any], dict[str, Any], Path, bytes]:
    exam = load_exam(exam_id)
    source = _find_question(exam, question_number)
    folder = resolve_variant_dir(exam_id, str(source.get("id", "")))
    if folder is None:
        raise HTTPException(status_code=404, detail="variant_not_found")
    raw = (folder / "question.json").read_bytes()
    try:
        question = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="invalid_variant") from exc
    if not isinstance(question, dict) or not isinstance(question.get("choices"), list):
        raise HTTPException(status_code=500, detail="invalid_variant")
    return exam, question, folder, raw


def load_question_snapshot(exam_id: str, question_number: int) -> QuestionSnapshot:
    exam = load_exam(exam_id)
    question = _find_question(exam, question_number)

    assets_by_id = {asset["id"]: asset for asset in exam["assets"]}
    stem_assets = _load_assets(
        exam_id=exam_id,
        asset_ids=question.get("shared_asset_refs", []),
        assets_by_id=assets_by_id,
        label_prefix="Stem",
    )
    choice_assets = {
        choice["label"]: _load_assets(
            exam_id=exam_id,
            asset_ids=choice.get("asset_refs", []),
            assets_by_id=assets_by_id,
            label_prefix=f"Choice {choice['label']}",
        )
        for choice in question.get("choices", [])
    }
    choices = [
        {
            "label": str(choice["label"]),
            "text": str(choice.get("text", "")),
        }
        for choice in question.get("choices", [])
    ]
    choice_labels = {choice["label"] for choice in choices}
    correct_label = str(exam.get("answer_key", {}).get(str(question_number), "")).upper()
    if not correct_label or correct_label not in choice_labels:
        raise HTTPException(status_code=500, detail="invalid_answer_key")
    return QuestionSnapshot(
        exam_id=exam_id,
        year=int(exam["year"]),
        level=str(exam["level"]),
        language=str(exam["language"]),
        question_number=question_number,
        stem_text=str(question.get("stem_text", "")),
        correct_label=correct_label,
        choices=choices,
        stem_assets=stem_assets,
        choice_assets=choice_assets,
    )


def validate_selected_label(snapshot: QuestionSnapshot, selected_label: str | None) -> str | None:
    if selected_label is None:
        return None
    labels = {choice["label"] for choice in snapshot.choices}
    if selected_label not in labels:
        raise HTTPException(status_code=422, detail="invalid_selected_label")
    return selected_label


def _load_assets(
    *,
    exam_id: str,
    asset_ids: list[str],
    assets_by_id: dict[str, dict[str, Any]],
    label_prefix: str,
) -> list[QuestionAsset]:
    items: list[QuestionAsset] = []
    for index, asset_id in enumerate(asset_ids, start=1):
        asset = assets_by_id.get(asset_id)
        if not asset:
            continue
        asset_path = release_root() / "exams" / exam_id / asset["path"]
        if not asset_path.is_file():
            continue
        media_type = str(asset.get("media_type", "application/octet-stream"))
        encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
        items.append(
            QuestionAsset(
                id=str(asset["id"]),
                label=f"{label_prefix} image {index}",
                role=str(asset.get("role", "")),
                media_type=media_type,
                data_url=f"data:{media_type};base64,{encoded}",
            )
        )
    return items


def _find_question(exam: dict[str, Any], question_number: int) -> dict[str, Any]:
    question = next(
        (item for item in exam["questions"] if int(item["number"]) == question_number),
        None,
    )
    if question is None:
        raise HTTPException(status_code=404, detail="question_not_found")
    return question
