from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional runtime dependency
    load_dotenv = None  # type: ignore[assignment]


@dataclass(frozen=True)
class Settings:
    release_data_path: Path
    openai_api_key: str | None
    openai_tts_model: str
    openai_tts_voice: str
    openai_explanation_model: str
    api_cache_dir: Path
    tts_cache_ttl_seconds: int
    tts_cache_max_items: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    if load_dotenv is not None:
        # Ensure local dev picks up repository-level .env values.
        load_dotenv(project_root / ".env", override=False)

    release_data_path = os.environ.get("RELEASE_DATA_PATH")
    if release_data_path:
        release_root = Path(release_data_path).resolve()
    else:
        release_root = project_root / "release-data"

    cache_dir = Path(os.environ.get("API_CACHE_DIR", "/tmp/math-api-cache")).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        release_data_path=release_root,
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        openai_tts_model=os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        openai_tts_voice=os.environ.get("OPENAI_TTS_VOICE", "alloy"),
        openai_explanation_model=os.environ.get("OPENAI_EXPLANATION_MODEL", "gpt-5.4"),
        api_cache_dir=cache_dir,
        tts_cache_ttl_seconds=int(os.environ.get("TTS_CACHE_TTL_SECONDS", "86400")),
        tts_cache_max_items=int(os.environ.get("TTS_CACHE_MAX_ITEMS", "500")),
    )
