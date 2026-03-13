from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .config import Settings, get_settings
from .exam_repository import (
    EmptyStemTextError,
    ExamNotFoundError,
    QuestionNotFoundError,
)
from .exam_repository import ExamRepository
from .openai_tts import OpenAITTSClient, TTSUpstreamError
from .stem_audio_service import PreparedStemAudio, StemAudioService


def create_app(
    *,
    settings: Settings | None = None,
    stem_audio_service: StemAudioService | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    if stem_audio_service is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required to start the FastAPI TTS backend.")

        exam_repository = ExamRepository(settings.exam_data_dir)
        tts_client = OpenAITTSClient(
            api_key=settings.openai_api_key,
            model=settings.tts_model,
            voice=settings.tts_voice,
            response_format=settings.tts_response_format,
            timeout_seconds=settings.tts_timeout_seconds,
        )
        stem_audio_service = StemAudioService(
            exam_repository=exam_repository,
            tts_client=tts_client,
            cache_dir=settings.tts_cache_dir,
            model=settings.tts_model,
            voice=settings.tts_voice,
            response_format=settings.tts_response_format,
        )

    app = FastAPI(title="Kangaroo Math TTS API")
    app.state.settings = settings
    app.state.stem_audio_service = stem_audio_service

    api_router = APIRouter(prefix="/api")

    @api_router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api_router.get("/tts/exams/{exam_id}/questions/{question_id}/stem.wav")
    def get_stem_audio(exam_id: str, question_id: int, request: Request):
        service: StemAudioService = request.app.state.stem_audio_service

        try:
            prepared = service.prepare_audio(exam_id, question_id)
        except (ExamNotFoundError, QuestionNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except EmptyStemTextError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except TTSUpstreamError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

        return _build_audio_response(prepared)

    app.include_router(api_router)

    if settings.frontend_dist_dir.exists():
        _register_frontend_routes(app, settings.frontend_dist_dir)

    return app


def _build_audio_response(prepared: PreparedStemAudio):
    headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "ETag": f"\"{prepared.asset.cache_key}\"",
    }

    if prepared.cached_path is not None:
        return FileResponse(
            prepared.cached_path,
            media_type="audio/wav",
            headers=headers,
        )

    if prepared.stream is None:
        raise RuntimeError("Prepared audio response is missing both cache path and stream.")

    return StreamingResponse(
        prepared.stream,
        media_type="audio/wav",
        headers=headers,
    )


def _register_frontend_routes(app: FastAPI, frontend_dist_dir: Path) -> None:
    frontend_dist_dir = frontend_dist_dir.resolve()

    def _resolve_path(requested_path: str) -> Path:
        candidate = (frontend_dist_dir / requested_path).resolve()
        if not candidate.is_relative_to(frontend_dist_dir):
            raise HTTPException(status_code=404, detail="File not found.")
        return candidate

    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(frontend_dist_dir / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_asset(full_path: str):
        candidate = _resolve_path(full_path)
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist_dir / "index.html")


def _create_default_app() -> FastAPI:
    settings = get_settings()
    if settings.openai_api_key:
        return create_app(settings=settings)

    app = FastAPI(title="Kangaroo Math TTS API")

    @app.get("/api/health")
    def health() -> JSONResponse:
        return JSONResponse(
            {"status": "misconfigured", "detail": "OPENAI_API_KEY is required."},
            status_code=500,
        )

    @app.get("/api/tts/exams/{exam_id}/questions/{question_id}/stem.wav")
    def tts_not_configured(exam_id: str, question_id: int) -> JSONResponse:
        del exam_id, question_id
        return JSONResponse(
            {"detail": "OPENAI_API_KEY is required to serve TTS audio."},
            status_code=500,
        )

    if settings.frontend_dist_dir.exists():
        _register_frontend_routes(app, settings.frontend_dist_dir)

    return app


app = _create_default_app()
