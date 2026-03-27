from __future__ import annotations

from fastapi import APIRouter

from ..question_loader import load_exam, load_manifest

router = APIRouter()


@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@router.get("/manifest")
def get_manifest() -> dict:
    return load_manifest()


@router.get("/exams/{exam_id}")
def get_exam(exam_id: str) -> dict:
    return load_exam(exam_id)
