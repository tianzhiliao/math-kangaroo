from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from ..config import get_settings


class ExplanationCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (get_settings().api_cache_dir / "explanations")
        self.root.mkdir(parents=True, exist_ok=True)

    def build_key(self, payload: dict[str, Any]) -> str:
        stable = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(stable.encode("utf-8")).hexdigest()

    def load(self, key: str) -> dict[str, Any] | None:
        path = self._path_for_key(key)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def store(self, key: str, payload: dict[str, Any]) -> None:
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _path_for_key(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"


class TTSAudioCache:
    def __init__(
        self,
        root: Path | None = None,
        *,
        ttl_seconds: int = 60 * 60 * 24,
        max_items: int = 500,
    ) -> None:
        self.root = root or (get_settings().api_cache_dir / "tts")
        self.root.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = max(0, int(ttl_seconds))
        self.max_items = max(0, int(max_items))

    def build_key(self, payload: dict[str, Any]) -> str:
        stable = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(stable.encode("utf-8")).hexdigest()

    def load(self, key: str) -> bytes | None:
        path = self._path_for_key(key)
        if not path.is_file():
            return None
        if self.ttl_seconds > 0:
            age_seconds = time.time() - path.stat().st_mtime
            if age_seconds > self.ttl_seconds:
                path.unlink(missing_ok=True)
                return None
        return path.read_bytes()

    def store(self, key: str, payload: bytes) -> None:
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        self._prune_if_needed()

    def _path_for_key(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.bin"

    def _prune_if_needed(self) -> None:
        if self.max_items <= 0:
            return
        files = sorted(
            self.root.glob("*/*.bin"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for stale in files[self.max_items :]:
            stale.unlink(missing_ok=True)
