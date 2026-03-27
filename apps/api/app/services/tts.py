from __future__ import annotations

from collections.abc import Iterator
import logging
import time

from fastapi import HTTPException

from ..config import get_settings
from ..openai_client import get_openai_client
from ..question_loader import load_question_stem_text
from ..schemas import AudioFormat
from .cache import TTSAudioCache

logger = logging.getLogger(__name__)


def audio_media_type(format_name: AudioFormat) -> str:
    return {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "pcm": "audio/pcm",
    }[format_name]


def stream_question_tts(
    *,
    exam_id: str,
    question_number: int,
    voice: str | None,
    speed: float,
    format_name: AudioFormat,
) -> Iterator[bytes]:
    started_at = time.perf_counter()
    stem_text = load_question_stem_text(exam_id, question_number)
    lookup_ms = (time.perf_counter() - started_at) * 1000
    if not stem_text.strip():
        raise HTTPException(status_code=422, detail="no_stem_text")

    settings = get_settings()
    cache = TTSAudioCache(
        ttl_seconds=settings.tts_cache_ttl_seconds,
        max_items=settings.tts_cache_max_items,
    )
    try:
        client = get_openai_client()
    except RuntimeError as exc:  # pragma: no cover - runtime-only paths
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    chosen_voice = voice or settings.openai_tts_voice
    cache_key = cache.build_key(
        {
            "exam_id": exam_id,
            "question_number": question_number,
            "voice": chosen_voice,
            "speed": speed,
            "format": format_name,
            "model": settings.openai_tts_model,
            "input": stem_text,
        }
    )
    cached_audio = cache.load(cache_key)
    if cached_audio is not None:
        logger.info(
            "tts cache hit exam_id=%s question=%s lookup_ms=%.1f bytes=%s",
            exam_id,
            question_number,
            lookup_ms,
            len(cached_audio),
        )

        def iterate_cached() -> Iterator[bytes]:
            yield cached_audio

        return iterate_cached()

    def iterate() -> Iterator[bytes]:
        model_started_at = time.perf_counter()
        first_chunk_at: float | None = None
        audio_parts: list[bytes] = []
        with client.audio.speech.with_streaming_response.create(
            model=settings.openai_tts_model,
            voice=chosen_voice,
            input=stem_text,
            speed=speed,
            response_format=format_name,
        ) as response:
            for chunk in response.iter_bytes():
                if chunk:
                    audio_parts.append(chunk)
                    if first_chunk_at is None:
                        first_chunk_at = time.perf_counter()
                    yield chunk

        total_bytes = sum(len(part) for part in audio_parts)
        if total_bytes > 0:
            cache.store(cache_key, b"".join(audio_parts))
        finished_at = time.perf_counter()
        first_chunk_ms = (
            (first_chunk_at - model_started_at) * 1000 if first_chunk_at is not None else -1.0
        )
        total_stream_ms = (finished_at - model_started_at) * 1000
        logger.info(
            "tts generated exam_id=%s question=%s lookup_ms=%.1f first_chunk_ms=%.1f total_stream_ms=%.1f bytes=%s",
            exam_id,
            question_number,
            lookup_ms,
            first_chunk_ms,
            total_stream_ms,
            total_bytes,
        )

    return iterate()
