from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ..schemas import AudioFormat, TTSRequest
from ..services.tts import audio_media_type, stream_question_tts

router = APIRouter()


def _build_tts_streaming_response(
    *,
    exam_id: str,
    question_number: int,
    voice: str | None,
    speed: float,
    format_name: AudioFormat,
) -> StreamingResponse:
    stream = stream_question_tts(
        exam_id=exam_id,
        question_number=question_number,
        voice=voice,
        speed=speed,
        format_name=format_name,
    )
    return StreamingResponse(stream, media_type=audio_media_type(format_name))


@router.post("/tts")
def tts(payload: TTSRequest):
    return _build_tts_streaming_response(
        exam_id=payload.exam_id,
        question_number=payload.question_number,
        voice=payload.voice,
        speed=payload.speed,
        format_name=payload.format,
    )


@router.get("/tts")
def tts_get(
    exam_id: str = Query(min_length=1),
    question_number: int = Query(ge=1),
    voice: str | None = None,
    speed: float = Query(default=1.0, ge=0.25, le=4.0),
    format: AudioFormat = "opus",
):
    return _build_tts_streaming_response(
        exam_id=exam_id,
        question_number=question_number,
        voice=voice,
        speed=speed,
        format_name=format,
    )
