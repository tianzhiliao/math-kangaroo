from __future__ import annotations

from functools import lru_cache

from .config import get_settings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - exercised indirectly in runtime checks
    OpenAI = None  # type: ignore[assignment]


@lru_cache(maxsize=1)
def get_openai_client():
    settings = get_settings()
    if OpenAI is None:
        raise RuntimeError("openai_package_missing")
    if not settings.openai_api_key:
        raise RuntimeError("openai_api_key_missing")
    return OpenAI(api_key=settings.openai_api_key)
