from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.config import get_settings
from app.main import create_app
from app.openai_client import get_openai_client
from app.question_loader import load_question_snapshot
from app.services.cache import ExplanationCache


class _FakeSpeechStreamResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_bytes(self):
        yield b"audio-1"
        yield b"audio-2"


class _FakeSpeechStreamingAPI:
    def __init__(self) -> None:
        self.last_create_kwargs: dict | None = None
        self.call_count = 0

    def create(self, **kwargs):
        self.last_create_kwargs = kwargs
        self.call_count += 1
        return _FakeSpeechStreamResponse()


class _FakeResponsesAPI:
    def __init__(self, outputs: list[dict[str, str]] | None = None) -> None:
        self.last_create_kwargs: dict | None = None
        self.call_count = 0
        self._outputs = outputs or [
            {
                "explanation": "Count slowly. Flower B matches both rules. So the answer is B.",
                "final_answer": "B",
            }
        ]

    def create(self, **kwargs):
        self.last_create_kwargs = kwargs
        self.call_count += 1
        payload = self._outputs[min(self.call_count - 1, len(self._outputs) - 1)]
        return type(
            "FakeResponse",
            (),
            {"output_text": json.dumps(payload)},
        )()


class _FakeOpenAIClient:
    def __init__(self, explanation_outputs: list[dict[str, str]] | None = None) -> None:
        self.speech_streaming = _FakeSpeechStreamingAPI()
        self.responses = _FakeResponsesAPI(explanation_outputs)
        self.audio = type(
            "FakeAudioAPI",
            (),
            {
                "speech": type(
                    "FakeSpeechAPI",
                    (),
                    {"with_streaming_response": self.speech_streaming},
                )()
            },
        )()


class ApiAiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.release_root = Path(self._temp_dir.name) / "release-data"
        self.release_root.mkdir(parents=True, exist_ok=True)
        self._build_fixture_release_data(self.release_root)
        self.cache_dir = Path(self._temp_dir.name) / "cache"
        os.environ["RELEASE_DATA_PATH"] = str(self.release_root)
        os.environ["API_CACHE_DIR"] = str(self.cache_dir)
        os.environ["OPENAI_API_KEY"] = "test-key"
        get_settings.cache_clear()
        get_openai_client.cache_clear()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        get_settings.cache_clear()
        get_openai_client.cache_clear()
        os.environ.pop("RELEASE_DATA_PATH", None)
        os.environ.pop("API_CACHE_DIR", None)
        os.environ.pop("OPENAI_API_KEY", None)
        self._temp_dir.cleanup()

    def test_question_lookup_reads_snapshot(self) -> None:
        snapshot = load_question_snapshot("sample-exam", 1)
        self.assertEqual(snapshot.correct_label, "B")
        self.assertEqual(snapshot.stem_text, "Pick the flower with 5 petals and 3 leaves.")
        self.assertEqual(snapshot.choices[0]["label"], "A")
        self.assertEqual(len(snapshot.stem_assets), 1)
        self.assertEqual(len(snapshot.choice_assets["A"]), 1)

    def test_tts_rejects_empty_stem(self) -> None:
        response = self.client.post(
            "/tts",
            json={"exam_id": "sample-exam", "question_number": 2},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "no_stem_text")

    def test_tts_streams_audio(self) -> None:
        fake_client = _FakeOpenAIClient()
        with patch("app.services.tts.get_openai_client", return_value=fake_client):
            response = self.client.post(
                "/tts",
                json={"exam_id": "sample-exam", "question_number": 1, "format": "mp3"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/mpeg")
        self.assertEqual(response.content, b"audio-1audio-2")
        self.assertEqual(fake_client.speech_streaming.last_create_kwargs["model"], "gpt-4o-mini-tts")
        self.assertEqual(
            fake_client.speech_streaming.last_create_kwargs["input"],
            "Pick the flower with 5 petals and 3 leaves.",
        )

    def test_tts_get_streams_audio(self) -> None:
        fake_client = _FakeOpenAIClient()
        with patch("app.services.tts.get_openai_client", return_value=fake_client):
            response = self.client.get(
                "/tts",
                params={"exam_id": "sample-exam", "question_number": 1, "format": "opus"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/opus")
        self.assertEqual(response.content, b"audio-1audio-2")
        self.assertEqual(
            fake_client.speech_streaming.last_create_kwargs["response_format"],
            "opus",
        )

    def test_tts_get_rejects_invalid_speed(self) -> None:
        response = self.client.get(
            "/tts",
            params={"exam_id": "sample-exam", "question_number": 1, "speed": 5},
        )
        self.assertEqual(response.status_code, 422)

    def test_tts_uses_opus_by_default(self) -> None:
        fake_client = _FakeOpenAIClient()
        with patch("app.services.tts.get_openai_client", return_value=fake_client):
            response = self.client.post(
                "/tts",
                json={"exam_id": "sample-exam", "question_number": 1},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/opus")
        self.assertEqual(
            fake_client.speech_streaming.last_create_kwargs["response_format"],
            "opus",
        )

    def test_tts_uses_cache_on_repeat(self) -> None:
        fake_client = _FakeOpenAIClient()
        with patch("app.services.tts.get_openai_client", return_value=fake_client):
            first = self.client.post(
                "/tts",
                json={"exam_id": "sample-exam", "question_number": 1, "format": "opus"},
            )
            second = self.client.post(
                "/tts",
                json={"exam_id": "sample-exam", "question_number": 1, "format": "opus"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.content, b"audio-1audio-2")
        self.assertEqual(second.content, b"audio-1audio-2")
        self.assertEqual(fake_client.speech_streaming.call_count, 1)

    def test_explanation_cache_key_changes_with_selected_label(self) -> None:
        cache = ExplanationCache(self.cache_dir)
        key_a = cache.build_key(
            {
                "exam_id": "sample-exam",
                "question_number": 1,
                "selected_label": "A",
                "model": "gpt-5.4",
                "prompt_version": "grade1_v2",
            }
        )
        key_b = cache.build_key(
            {
                "exam_id": "sample-exam",
                "question_number": 1,
                "selected_label": "B",
                "model": "gpt-5.4",
                "prompt_version": "grade1_v2",
            }
        )
        self.assertNotEqual(key_a, key_b)

    def test_explanation_route_returns_schema_and_uses_cache(self) -> None:
        fake_client = _FakeOpenAIClient()
        with patch("app.services.explanations.get_openai_client", return_value=fake_client):
            first = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "D"},
            )
        self.assertEqual(first.status_code, 200)
        first_json = first.json()
        self.assertEqual(first_json["correct_label"], "B")
        self.assertEqual(first_json["selected_label"], "D")
        self.assertEqual(first_json["model"], "gpt-5.4")
        self.assertFalse(first_json["cache_hit"])
        self.assertIn("So the answer is B.", first_json["explanation"])
        self.assertIsNotNone(fake_client.responses.last_create_kwargs)

        with patch("app.services.explanations.get_openai_client", side_effect=AssertionError("cache should be used")):
            second = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "D"},
            )
        self.assertEqual(second.status_code, 200)
        second_json = second.json()
        self.assertTrue(second_json["cache_hit"])
        self.assertEqual(second_json["explanation"], first_json["explanation"])

    def test_explanation_rejects_invalid_selected_label(self) -> None:
        response = self.client.post(
            "/ai/explanation",
            json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "Z"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "invalid_selected_label")

    def test_explanation_force_refresh_bypasses_cache_and_overwrites(self) -> None:
        first_client = _FakeOpenAIClient(
            explanation_outputs=[
                {
                    "explanation": "First explanation from model.",
                    "final_answer": "B",
                }
            ]
        )
        with patch("app.services.explanations.get_openai_client", return_value=first_client):
            first = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "D"},
            )
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        self.assertFalse(first_payload["cache_hit"])
        self.assertEqual(first_client.responses.call_count, 1)

        with patch("app.services.explanations.get_openai_client", side_effect=AssertionError("cache should be used")):
            cached = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "D"},
            )
        self.assertEqual(cached.status_code, 200)
        cached_payload = cached.json()
        self.assertTrue(cached_payload["cache_hit"])
        self.assertEqual(cached_payload["explanation"], first_payload["explanation"])

        refreshed_client = _FakeOpenAIClient(
            explanation_outputs=[
                {
                    "explanation": "Fresh regenerated explanation.",
                    "final_answer": "B",
                }
            ]
        )
        with patch("app.services.explanations.get_openai_client", return_value=refreshed_client):
            refreshed = self.client.post(
                "/ai/explanation",
                json={
                    "exam_id": "sample-exam",
                    "question_number": 1,
                    "selected_label": "D",
                    "force_refresh": True,
                },
            )
        self.assertEqual(refreshed.status_code, 200)
        refreshed_payload = refreshed.json()
        self.assertFalse(refreshed_payload["cache_hit"])
        self.assertIn("Fresh regenerated explanation.", refreshed_payload["explanation"])
        self.assertEqual(refreshed_client.responses.call_count, 1)

        with patch("app.services.explanations.get_openai_client", side_effect=AssertionError("updated cache should be used")):
            after_refresh = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "D"},
            )
        self.assertEqual(after_refresh.status_code, 200)
        after_refresh_payload = after_refresh.json()
        self.assertTrue(after_refresh_payload["cache_hit"])
        self.assertEqual(
            after_refresh_payload["explanation"],
            refreshed_payload["explanation"],
        )

    def test_explanation_retries_when_final_answer_mismatches(self) -> None:
        fake_client = _FakeOpenAIClient(
            explanation_outputs=[
                {
                    "explanation": "I think this one is C because of the shape.",
                    "final_answer": "C",
                },
                {
                    "explanation": "Check each clue carefully. Option B matches both clues.",
                    "final_answer": "B",
                },
            ]
        )
        with patch("app.services.explanations.get_openai_client", return_value=fake_client):
            response = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "A"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["correct_label"], "B")
        self.assertIn("So the answer is B.", payload["explanation"])
        self.assertEqual(fake_client.responses.call_count, 2)

    def test_explanation_retries_when_text_contradicts_answer(self) -> None:
        fake_client = _FakeOpenAIClient(
            explanation_outputs=[
                {
                    "explanation": "We count carefully and see that the answer is C.",
                    "final_answer": "B",
                },
                {
                    "explanation": "Follow each clue and compare each option. Option B is correct.",
                    "final_answer": "B",
                },
            ]
        )
        with patch("app.services.explanations.get_openai_client", return_value=fake_client):
            response = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "C"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["correct_label"], "B")
        self.assertIn("So the answer is B.", payload["explanation"])
        self.assertEqual(fake_client.responses.call_count, 2)

    def test_explanation_uses_fallback_and_caches_only_valid_result(self) -> None:
        fake_client = _FakeOpenAIClient(
            explanation_outputs=[
                {
                    "explanation": "This says the answer is D.",
                    "final_answer": "D",
                },
                {
                    "explanation": "This says the answer is E.",
                    "final_answer": "E",
                },
            ]
        )
        with patch("app.services.explanations.get_openai_client", return_value=fake_client):
            first = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "A"},
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(fake_client.responses.call_count, 2)
        first_payload = first.json()
        self.assertIn("So the answer is B.", first_payload["explanation"])

        with patch("app.services.explanations.get_openai_client", side_effect=AssertionError("cache should be used")):
            second = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "A"},
            )
        self.assertEqual(second.status_code, 200)
        second_payload = second.json()
        self.assertTrue(second_payload["cache_hit"])
        self.assertEqual(second_payload["explanation"], first_payload["explanation"])

    def test_snapshot_rejects_invalid_answer_key(self) -> None:
        exam_path = self.release_root / "exams" / "sample-exam" / "exam.json"
        payload = json.loads(exam_path.read_text(encoding="utf-8"))
        payload["answer_key"]["1"] = "Z"
        exam_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        response = self.client.post(
            "/ai/explanation",
            json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "A"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "invalid_answer_key")

    def _build_fixture_release_data(self, root: Path) -> None:
        (root / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "generated_at": "2026-03-20T00:00:00Z",
                    "exams": [
                        {
                            "exam_id": "sample-exam",
                            "path": "exams/sample-exam/exam.json",
                            "family": "sample_family",
                            "year": 2026,
                            "level": "grade-1-2",
                            "language": "en",
                            "question_count": 2,
                            "asset_count": 6,
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        exam_dir = root / "exams" / "sample-exam"
        asset_dir = exam_dir / "assets"
        asset_dir.mkdir(parents=True, exist_ok=True)
        for name in [
            "q01_stem_01.png",
            "q01_option_A_01.png",
            "q01_option_B_01.png",
            "q01_option_C_01.png",
            "q01_option_D_01.png",
            "q01_option_E_01.png",
        ]:
            (asset_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n")

        exam_payload = {
            "exam_id": "sample-exam",
            "year": 2026,
            "family": "sample_family",
            "level": "grade-1-2",
            "language": "en",
            "duration_minutes": 45,
            "question_count": 2,
            "scoring_rules": [{"from": 1, "to": 2, "points": 3}],
            "instructions": ["Read carefully."],
            "answer_key": {"1": "B", "2": "A"},
            "assets": [
                {
                    "id": "q01_stem_01",
                    "path": "assets/q01_stem_01.png",
                    "format": "png",
                    "media_type": "image/png",
                    "kind": "question_figure",
                    "role": "stem",
                    "width": 32,
                    "height": 32,
                },
                *[
                    {
                        "id": f"q01_option_{label}_01",
                        "path": f"assets/q01_option_{label}_01.png",
                        "format": "png",
                        "media_type": "image/png",
                        "kind": "question_figure",
                        "role": "option",
                        "width": 32,
                        "height": 32,
                    }
                    for label in ["A", "B", "C", "D", "E"]
                ],
            ],
            "questions": [
                {
                    "id": "q01",
                    "number": 1,
                    "part": "part_a",
                    "points": 3,
                    "stem_text": "Pick the flower with 5 petals and 3 leaves.",
                    "shared_asset_refs": ["q01_stem_01"],
                    "choices": [
                        {"label": "A", "text": "", "asset_refs": ["q01_option_A_01"]},
                        {"label": "B", "text": "", "asset_refs": ["q01_option_B_01"]},
                        {"label": "C", "text": "", "asset_refs": ["q01_option_C_01"]},
                        {"label": "D", "text": "", "asset_refs": ["q01_option_D_01"]},
                        {"label": "E", "text": "", "asset_refs": ["q01_option_E_01"]},
                    ],
                },
                {
                    "id": "q02",
                    "number": 2,
                    "part": "part_a",
                    "points": 3,
                    "stem_text": "",
                    "shared_asset_refs": [],
                    "choices": [
                        {"label": "A", "text": "1", "asset_refs": []},
                        {"label": "B", "text": "2", "asset_refs": []},
                        {"label": "C", "text": "3", "asset_refs": []},
                        {"label": "D", "text": "4", "asset_refs": []},
                        {"label": "E", "text": "5", "asset_refs": []},
                    ],
                },
            ],
        }
        (exam_dir / "exam.json").write_text(
            json.dumps(exam_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
