from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


AudioFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]


class TTSRequest(BaseModel):
    exam_id: str = Field(min_length=1)
    question_number: int = Field(ge=1)
    voice: str | None = None
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    format: AudioFormat = "opus"


class ExplanationRequest(BaseModel):
    exam_id: str = Field(min_length=1)
    question_number: int = Field(ge=1)
    selected_label: str | None = None
    force_refresh: bool = False

    @field_validator("selected_label")
    @classmethod
    def normalize_selected_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class ExplanationResponse(BaseModel):
    exam_id: str
    question_number: int
    selected_label: str | None = None
    correct_label: str
    explanation: str
    model: str
    cache_hit: bool
    generated_at: str
