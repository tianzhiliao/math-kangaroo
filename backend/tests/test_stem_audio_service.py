from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import threading
import unittest

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.exam_repository import EmptyStemTextError, ExamRepository
from backend.main import create_app
from backend.stem_audio_service import StemAudioService


AUDIO_BYTES = b"RIFFdemo-audio"


class FakeTTSClient:
    def __init__(self, payload: bytes = AUDIO_BYTES) -> None:
        self.payload = payload
        self.calls = 0
        self._lock = threading.Lock()

    def open_stream(self, text: str):
        del text
        with self._lock:
            self.calls += 1
        return BytesIO(self.payload)


class BlockingTTSClient(FakeTTSClient):
    def __init__(self, payload: bytes = AUDIO_BYTES) -> None:
        super().__init__(payload=payload)
        self.started = threading.Event()
        self.release = threading.Event()

    def open_stream(self, text: str):
        stream = super().open_stream(text)
        self.started.set()
        self.release.wait(timeout=2)
        return stream


class FailingStream(BytesIO):
    def __init__(self, chunks_before_failure: int) -> None:
        super().__init__(b"x" * 16)
        self._remaining_reads = chunks_before_failure

    def read(self, size: int = -1) -> bytes:
        if self._remaining_reads <= 0:
            raise RuntimeError("stream failed")
        self._remaining_reads -= 1
        return super().read(size)


class FailingTTSClient(FakeTTSClient):
    def open_stream(self, text: str):
        del text
        self.calls += 1
        return FailingStream(chunks_before_failure=1)


def write_exam_fixture(path: Path, *, stem_text: str = "Read me aloud") -> None:
    payload = {
        "paper_id": "Exam_2099",
        "questions": [
            {
                "id": 1,
                "stem_text": stem_text,
                "options": {"A": {"text": "1"}},
                "answer": "A",
                "points": 3,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class StemAudioServiceTests(unittest.TestCase):
    def create_service(self, temp_dir: str, client=None, *, stem_text: str = "Read me aloud") -> StemAudioService:
        root = Path(temp_dir)
        data_dir = root / "data"
        cache_dir = root / "cache"
        data_dir.mkdir(parents=True, exist_ok=True)
        write_exam_fixture(data_dir / "Exam_2099.json", stem_text=stem_text)

        repository = ExamRepository(data_dir)
        return StemAudioService(
            exam_repository=repository,
            tts_client=client or FakeTTSClient(),
            cache_dir=cache_dir,
            model="tts-1",
            voice="shimmer",
            response_format="wav",
        )

    def test_ensure_cached_audio_uses_cache_on_second_call(self) -> None:
        with TemporaryDirectory() as temp_dir:
            client = FakeTTSClient()
            service = self.create_service(temp_dir, client=client)

            first_path = service.ensure_cached_audio("Exam_2099", 1)
            second_path = service.ensure_cached_audio("Exam_2099", 1)

            self.assertEqual(first_path, second_path)
            self.assertTrue(first_path.is_file())
            self.assertEqual(first_path.read_bytes(), AUDIO_BYTES)
            self.assertEqual(client.calls, 1)

    def test_empty_stem_text_raises(self) -> None:
        with TemporaryDirectory() as temp_dir:
            service = self.create_service(temp_dir, stem_text="   ")

            with self.assertRaises(EmptyStemTextError):
                service.resolve_asset("Exam_2099", 1)

    def test_concurrent_generation_only_hits_upstream_once(self) -> None:
        with TemporaryDirectory() as temp_dir:
            client = BlockingTTSClient()
            service = self.create_service(temp_dir, client=client)

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_one = executor.submit(service.ensure_cached_audio, "Exam_2099", 1)
                client.started.wait(timeout=2)
                future_two = executor.submit(service.ensure_cached_audio, "Exam_2099", 1)
                client.release.set()

                path_one = future_one.result(timeout=2)
                path_two = future_two.result(timeout=2)

            self.assertEqual(path_one, path_two)
            self.assertEqual(client.calls, 1)

    def test_failed_generation_does_not_leave_partial_cache_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            client = FailingTTSClient()
            service = self.create_service(temp_dir, client=client)

            with self.assertRaises(RuntimeError):
                service.ensure_cached_audio("Exam_2099", 1)

            asset = service.resolve_asset("Exam_2099", 1)
            self.assertFalse(asset.cache_path.exists())


class FastAPITests(unittest.TestCase):
    def create_client(self, temp_dir: str, *, stem_text: str = "Read me aloud", tts_client=None) -> tuple[TestClient, FakeTTSClient]:
        root = Path(temp_dir)
        data_dir = root / "data"
        cache_dir = root / "cache"
        dist_dir = root / "dist"
        data_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        dist_dir.mkdir(parents=True, exist_ok=True)
        (dist_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
        write_exam_fixture(data_dir / "Exam_2099.json", stem_text=stem_text)

        fake_client = tts_client or FakeTTSClient()
        service = StemAudioService(
            exam_repository=ExamRepository(data_dir),
            tts_client=fake_client,
            cache_dir=cache_dir,
            model="tts-1",
            voice="shimmer",
            response_format="wav",
        )
        settings = Settings(
            openai_api_key="test",
            tts_model="tts-1",
            tts_voice="shimmer",
            tts_response_format="wav",
            tts_timeout_seconds=45.0,
            exam_data_dir=data_dir,
            tts_cache_dir=cache_dir,
            frontend_dist_dir=dist_dir,
        )
        app = create_app(settings=settings, stem_audio_service=service)
        return TestClient(app), fake_client

    def test_audio_endpoint_returns_wav_and_reuses_cache(self) -> None:
        with TemporaryDirectory() as temp_dir:
            client, fake_tts = self.create_client(temp_dir)

            first = client.get("/api/tts/exams/Exam_2099/questions/1/stem.wav")
            second = client.get("/api/tts/exams/Exam_2099/questions/1/stem.wav")

            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.headers["content-type"], "audio/wav")
            self.assertEqual(first.content, AUDIO_BYTES)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(fake_tts.calls, 1)

    def test_audio_endpoint_returns_404_for_missing_question(self) -> None:
        with TemporaryDirectory() as temp_dir:
            client, _ = self.create_client(temp_dir)

            response = client.get("/api/tts/exams/Exam_2099/questions/99/stem.wav")

            self.assertEqual(response.status_code, 404)

    def test_audio_endpoint_returns_422_for_empty_stem(self) -> None:
        with TemporaryDirectory() as temp_dir:
            client, _ = self.create_client(temp_dir, stem_text="  ")

            response = client.get("/api/tts/exams/Exam_2099/questions/1/stem.wav")

            self.assertEqual(response.status_code, 422)
