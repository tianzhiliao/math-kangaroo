from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO_ROOT / "kangaroo-math-mvp"
EXAM_DATA_DIR = FRONTEND_ROOT / "public" / "data"
FRONTEND_DIST_DIR = FRONTEND_ROOT / "dist"
DEFAULT_CACHE_DIR = REPO_ROOT / ".cache" / "tts"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]

        os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    tts_model: str
    tts_voice: str
    tts_response_format: str
    tts_timeout_seconds: float
    exam_data_dir: Path
    tts_cache_dir: Path
    frontend_dist_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_env_file(REPO_ROOT / ".env")
    load_env_file(FRONTEND_ROOT / ".env")

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        tts_model=os.getenv("TTS_MODEL", "tts-1"),
        tts_voice=os.getenv("TTS_VOICE", "shimmer"),
        tts_response_format=os.getenv("TTS_RESPONSE_FORMAT", "wav"),
        tts_timeout_seconds=float(os.getenv("TTS_TIMEOUT_SECONDS", "45")),
        exam_data_dir=Path(os.getenv("EXAM_DATA_DIR", EXAM_DATA_DIR)).resolve(),
        tts_cache_dir=Path(os.getenv("TTS_CACHE_DIR", DEFAULT_CACHE_DIR)).resolve(),
        frontend_dist_dir=Path(os.getenv("FRONTEND_DIST_DIR", FRONTEND_DIST_DIR)).resolve(),
    )

