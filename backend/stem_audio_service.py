from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import os
import tempfile
import threading

from .exam_repository import ExamRepository, ExamStem


CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class StemAudioAsset:
    exam_id: str
    question_id: int
    stem_text: str
    cache_key: str
    version: str
    cache_path: Path


@dataclass
class PreparedStemAudio:
    asset: StemAudioAsset
    cached_path: Path | None = None
    stream: Iterator[bytes] | None = None


class StemAudioService:
    def __init__(
        self,
        *,
        exam_repository: ExamRepository,
        tts_client,
        cache_dir: Path,
        model: str,
        voice: str,
        response_format: str,
    ) -> None:
        self._exam_repository = exam_repository
        self._tts_client = tts_client
        self._cache_dir = cache_dir
        self._model = model
        self._voice = voice
        self._response_format = response_format
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def list_stems(self) -> list[ExamStem]:
        return self._exam_repository.list_stems()

    def resolve_asset(self, exam_id: str, question_id: int) -> StemAudioAsset:
        stem = self._exam_repository.get_stem(exam_id, question_id)
        cache_key = self._build_cache_key(stem)
        version = cache_key[:16]
        cache_path = self._cache_dir / stem.exam_id / f"{stem.question_id}-{cache_key}.{self._response_format}"
        return StemAudioAsset(
            exam_id=stem.exam_id,
            question_id=stem.question_id,
            stem_text=stem.stem_text,
            cache_key=cache_key,
            version=version,
            cache_path=cache_path,
        )

    def ensure_cached_audio(self, exam_id: str, question_id: int) -> Path:
        asset = self.resolve_asset(exam_id, question_id)
        cached_path = self._try_cached_path(asset)
        if cached_path is not None:
            return cached_path

        lock = self._acquire_lock(asset.cache_key)
        with lock:
            cached_path = self._try_cached_path(asset)
            if cached_path is not None:
                return cached_path

            upstream = self._tts_client.open_stream(asset.stem_text)
            return self._write_stream_to_cache(asset, upstream)

    def prepare_audio(self, exam_id: str, question_id: int) -> PreparedStemAudio:
        asset = self.resolve_asset(exam_id, question_id)
        cached_path = self._try_cached_path(asset)
        if cached_path is not None:
            return PreparedStemAudio(asset=asset, cached_path=cached_path)

        lock = self._acquire_lock(asset.cache_key)
        lock.acquire()
        cached_path = self._try_cached_path(asset)
        if cached_path is not None:
            lock.release()
            return PreparedStemAudio(asset=asset, cached_path=cached_path)

        try:
            upstream = self._tts_client.open_stream(asset.stem_text)
        except Exception:
            lock.release()
            raise

        return PreparedStemAudio(
            asset=asset,
            stream=self._stream_to_cache(asset, upstream, lock),
        )

    def _try_cached_path(self, asset: StemAudioAsset) -> Path | None:
        if asset.cache_path.is_file() and asset.cache_path.stat().st_size > 0:
            return asset.cache_path
        return None

    def _build_cache_key(self, stem: ExamStem) -> str:
        key = "\n".join(
            [
                stem.exam_id,
                str(stem.question_id),
                stem.stem_text,
                self._model,
                self._voice,
                self._response_format,
            ]
        )
        return sha256(key.encode("utf-8")).hexdigest()

    def _acquire_lock(self, cache_key: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(cache_key)
            if lock is None:
                lock = threading.Lock()
                self._locks[cache_key] = lock
            return lock

    def _make_temp_path(self, asset: StemAudioAsset) -> Path:
        asset.cache_path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temp_name = tempfile.mkstemp(
            dir=asset.cache_path.parent,
            prefix=f"{asset.question_id}-",
            suffix=".tmp",
        )
        os.close(file_descriptor)
        return Path(temp_name)

    def _write_stream_to_cache(self, asset: StemAudioAsset, upstream) -> Path:
        temp_path = self._make_temp_path(asset)
        total_bytes = 0

        try:
            with upstream, temp_path.open("wb") as handle:
                while True:
                    chunk = upstream.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    handle.write(chunk)
                    total_bytes += len(chunk)

            if total_bytes <= 0:
                raise RuntimeError("OpenAI TTS returned an empty audio payload.")

            os.replace(temp_path, asset.cache_path)
            return asset.cache_path
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def _stream_to_cache(self, asset: StemAudioAsset, upstream, lock: threading.Lock) -> Iterator[bytes]:
        temp_path = self._make_temp_path(asset)

        def iterator() -> Iterator[bytes]:
            total_bytes = 0
            try:
                with upstream, temp_path.open("wb") as handle:
                    while True:
                        chunk = upstream.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        handle.write(chunk)
                        total_bytes += len(chunk)
                        yield chunk

                if total_bytes <= 0:
                    raise RuntimeError("OpenAI TTS returned an empty audio payload.")

                os.replace(temp_path, asset.cache_path)
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
            finally:
                lock.release()

        return iterator()

