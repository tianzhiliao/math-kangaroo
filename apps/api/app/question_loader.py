from __future__ import annotations

import base64
import json
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


def load_question_stem_text(exam_id: str, question_number: int) -> str:
    question = _find_question(load_exam(exam_id), question_number)
    return str(question.get("stem_text", ""))


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
