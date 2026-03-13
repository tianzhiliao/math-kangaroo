from __future__ import annotations

from collections import Counter
import sys

from backend.config import get_settings
from backend.exam_repository import ExamRepository
from backend.openai_tts import OpenAITTSClient
from backend.stem_audio_service import StemAudioService


def build_service() -> StemAudioService:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to prewarm the TTS cache.")

    exam_repository = ExamRepository(settings.exam_data_dir)
    tts_client = OpenAITTSClient(
        api_key=settings.openai_api_key,
        model=settings.tts_model,
        voice=settings.tts_voice,
        response_format=settings.tts_response_format,
        timeout_seconds=settings.tts_timeout_seconds,
    )
    return StemAudioService(
        exam_repository=exam_repository,
        tts_client=tts_client,
        cache_dir=settings.tts_cache_dir,
        model=settings.tts_model,
        voice=settings.tts_voice,
        response_format=settings.tts_response_format,
    )


def main() -> int:
    service = build_service()
    stems = service.list_stems()
    failures: list[str] = []
    counts = Counter()

    print(f"Prewarming {len(stems)} stem audio files...")
    for stem in stems:
        try:
            path = service.ensure_cached_audio(stem.exam_id, stem.question_id)
            counts["ok"] += 1
            print(f"[ok] {stem.exam_id} Q{stem.question_id} -> {path}")
        except Exception as exc:  # pragma: no cover - exercised by CLI use
            counts["failed"] += 1
            message = f"{stem.exam_id} Q{stem.question_id}: {exc}"
            failures.append(message)
            print(f"[failed] {message}", file=sys.stderr)

    print(f"Prewarm complete. success={counts['ok']} failed={counts['failed']}")
    if failures:
        print("Failures:", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

