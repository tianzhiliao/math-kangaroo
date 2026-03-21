"""FastAPI service for exams, TTS, and future AI generation."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Math prep API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def release_root() -> Path:
    env = os.environ.get("RELEASE_DATA_PATH")
    if env:
        return Path(env).resolve()
    # apps/api -> repo root
    return Path(__file__).resolve().parent.parent.parent / "release-data"


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/manifest")
def get_manifest() -> dict:
    path = release_root() / "manifest.json"
    if not path.is_file():
        raise HTTPException(status_code=500, detail="manifest_not_found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/exams/{exam_id}")
def get_exam(exam_id: str) -> dict:
    path = release_root() / "exams" / exam_id / "exam.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="exam_not_found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/tts")
def tts_stub(payload: dict | None = None) -> dict:
    """Placeholder for text-to-speech integration."""
    return {"status": "not_implemented", "audio_url": None, "body": payload}


@app.post("/ai/generate-similar")
def ai_generate_similar(payload: dict | None = None) -> dict:
    """Placeholder for LLM-generated similar questions."""
    return {"status": "not_implemented", "questions": [], "body": payload}
