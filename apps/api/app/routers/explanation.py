from __future__ import annotations

from fastapi import APIRouter

from ..schemas import ExplanationRequest, ExplanationResponse
from ..services.explanations import generate_explanation

router = APIRouter()


@router.post("/ai/explanation", response_model=ExplanationResponse)
def explanation(payload: ExplanationRequest) -> ExplanationResponse:
    return ExplanationResponse(
        **generate_explanation(
            exam_id=payload.exam_id,
            question_number=payload.question_number,
            selected_label=payload.selected_label,
            force_refresh=payload.force_refresh,
        )
    )
