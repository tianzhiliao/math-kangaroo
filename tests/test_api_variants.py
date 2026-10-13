"""API behaviour for AI-generated similar questions (``variant: true``)."""

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
sys.path.insert(0, str(ROOT / "tests"))

from app.config import get_settings
from app.main import create_app
from app.openai_client import get_openai_client
from app.question_loader import load_variant_snapshot, resolve_variant_dir
import test_api_ai
from test_api_ai import _FakeOpenAIClient

PNG = b"\x89PNG\r\n\x1a\n"


def _variant(stem: str, answer: str) -> dict:
    return {
        "id": "q01",
        "number": 1,
        "part": "part_a",
        "points": 3,
        "stem_text": stem,
        "answer": answer,
        "choices": [{"label": label, "text": str(i + 2), "asset_refs": []} for i, label in enumerate("ABCDE")],
        "shared_asset_refs": ["q01_stem_01"],
        "assets": [
            {
                "id": "q01_stem_01",
                "path": "figure.svg",
                "format": "svg",
                "media_type": "image/svg+xml",
                "kind": "question_figure",
                "role": "stem",
                "width": 100,
                "height": 50,
            }
        ],
    }


class ApiVariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        temp = Path(self._temp_dir.name)
        self.release_root = temp / "release-data"
        self.release_root.mkdir(parents=True)
        # Reuse the release fixture of the source-question tests.
        test_api_ai.ApiAiTests._build_fixture_release_data(self, self.release_root)  # type: ignore[arg-type]
        self._add_duplicate_exam()

        self.generated_root = temp / "generated"
        variant_dir = self.generated_root / "sample-exam" / "q01"
        variant_dir.mkdir(parents=True)
        (variant_dir / "question.json").write_text(
            json.dumps(_variant("Pick the bag with 4 apples.", "C")), encoding="utf-8"
        )
        (variant_dir / "figure.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"/>')
        (variant_dir / "card.png").write_bytes(PNG)
        (self.generated_root / "copy-exam").mkdir(parents=True)
        (self.generated_root / "copy-exam" / "manifest.json").write_text(
            json.dumps(
                {
                    "exam_id": "copy-exam",
                    "questions": [
                        {
                            "id": "q01",
                            "status": "skipped-duplicate",
                            "duplicate_of": "sample-exam",
                            "duplicate_question": "q01",
                            "answer": None,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        os.environ["RELEASE_DATA_PATH"] = str(self.release_root)
        os.environ["GENERATED_QUESTIONS_PATH"] = str(self.generated_root)
        os.environ["API_CACHE_DIR"] = str(temp / "cache")
        os.environ["OPENAI_API_KEY"] = "test-key"
        get_settings.cache_clear()
        get_openai_client.cache_clear()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        get_settings.cache_clear()
        get_openai_client.cache_clear()
        for key in ("RELEASE_DATA_PATH", "GENERATED_QUESTIONS_PATH", "API_CACHE_DIR", "OPENAI_API_KEY"):
            os.environ.pop(key, None)
        self._temp_dir.cleanup()

    def _add_duplicate_exam(self) -> None:
        source = json.loads((self.release_root / "exams" / "sample-exam" / "exam.json").read_text(encoding="utf-8"))
        copy = {**source, "exam_id": "copy-exam"}
        exam_dir = self.release_root / "exams" / "copy-exam"
        exam_dir.mkdir(parents=True)
        (exam_dir / "exam.json").write_text(json.dumps(copy), encoding="utf-8")

    def _explain(self, client: _FakeOpenAIClient, **payload):
        body = {"exam_id": "sample-exam", "question_number": 1, "selected_label": "A", "variant": True, **payload}
        with patch("app.services.explanations.get_openai_client", return_value=client):
            return self.client.post("/ai/explanation", json=body)

    def test_snapshot_uses_variant_answer_and_card_image(self) -> None:
        snapshot = load_variant_snapshot("sample-exam", 1)
        self.assertEqual(snapshot.correct_label, "C")
        self.assertEqual(snapshot.stem_text, "Pick the bag with 4 apples.")
        self.assertEqual([a.media_type for a in snapshot.stem_assets], ["image/png"])
        self.assertTrue(snapshot.variant_digest)

    def test_explanation_checks_against_variant_key(self) -> None:
        client = _FakeOpenAIClient(
            [
                # The source key (B) is wrong for the variant and must be rejected.
                {"explanation": "Bag B has 4 apples. So the answer is B.", "final_answer": "B"},
                {"explanation": "Count the apples in each bag. Bag C has 4.", "final_answer": "C"},
            ]
        )
        response = self._explain(client)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["correct_label"], "C")
        self.assertTrue(body["variant"])
        self.assertTrue(body["explanation"].endswith("So the answer is C."))
        self.assertEqual(client.responses.call_count, 2)

        user_content = client.responses.last_create_kwargs["input"][1]["content"]
        self.assertIn("Pick the bag with 4 apples.", user_content[0]["text"])
        self.assertIn("Correct answer: C", user_content[0]["text"])
        images = [part for part in user_content if part["type"] == "input_image"]
        self.assertEqual(len(images), 1)
        self.assertTrue(images[0]["image_url"].startswith("data:image/png;base64,"))

    def test_variant_and_source_explanations_are_cached_separately(self) -> None:
        variant_client = _FakeOpenAIClient([{"explanation": "Bag C has 4 apples.", "final_answer": "C"}])
        self.assertEqual(self._explain(variant_client).json()["correct_label"], "C")

        source_client = _FakeOpenAIClient()
        with patch("app.services.explanations.get_openai_client", return_value=source_client):
            source = self.client.post(
                "/ai/explanation",
                json={"exam_id": "sample-exam", "question_number": 1, "selected_label": "A"},
            ).json()
        self.assertEqual(source["correct_label"], "B")
        self.assertFalse(source["cache_hit"])
        self.assertFalse(source["variant"])

        repeat = self._explain(_FakeOpenAIClient())
        self.assertTrue(repeat.json()["cache_hit"])
        self.assertEqual(repeat.json()["correct_label"], "C")

    def test_regenerated_variant_invalidates_cache(self) -> None:
        self._explain(_FakeOpenAIClient([{"explanation": "Bag C has 4 apples.", "final_answer": "C"}]))
        path = self.generated_root / "sample-exam" / "q01" / "question.json"
        path.write_text(json.dumps(_variant("Pick the bag with 5 apples.", "D")), encoding="utf-8")

        response = self._explain(_FakeOpenAIClient([{"explanation": "Bag D has 5 apples.", "final_answer": "D"}]))
        self.assertFalse(response.json()["cache_hit"])
        self.assertEqual(response.json()["correct_label"], "D")

    def test_duplicate_question_uses_the_shared_variant(self) -> None:
        self.assertEqual(
            resolve_variant_dir("copy-exam", "q01"),
            (self.generated_root / "sample-exam" / "q01").resolve(),
        )
        response = self._explain(
            _FakeOpenAIClient([{"explanation": "Bag C has 4 apples.", "final_answer": "C"}]),
            exam_id="copy-exam",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["correct_label"], "C")

    def test_withdrawn_variant_is_404_also_for_its_duplicates(self) -> None:
        (self.generated_root / "sample-exam" / "manifest.json").write_text(
            json.dumps(
                {
                    "exam_id": "sample-exam",
                    "questions": [
                        {"id": "q01", "status": "withdrawn", "withdrawn_reason": "Two answers.", "answer": "C"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        for exam_id in ("sample-exam", "copy-exam"):
            with self.subTest(exam_id=exam_id):
                self.assertIsNone(resolve_variant_dir(exam_id, "q01"))
                response = self._explain(_FakeOpenAIClient(), exam_id=exam_id)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["detail"], "variant_not_found")

    def test_missing_variant_is_404(self) -> None:
        response = self._explain(_FakeOpenAIClient(), question_number=2)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "variant_not_found")

    def test_invalid_variant_answer_is_500(self) -> None:
        path = self.generated_root / "sample-exam" / "q01" / "question.json"
        path.write_text(json.dumps(_variant("Pick a bag.", "Z")), encoding="utf-8")
        response = self._explain(_FakeOpenAIClient())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "invalid_variant_answer")

    def test_provider_error_is_a_clean_502(self) -> None:
        import httpx
        from openai import AuthenticationError

        client = _FakeOpenAIClient()
        request = httpx.Request("POST", "https://api.openai.com/v1/responses")
        error = AuthenticationError(
            "account_deactivated", response=httpx.Response(401, request=request), body=None
        )

        def boom(**_kwargs):
            raise error

        client.responses.create = boom
        response = self._explain(client)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "ai_provider_error")

    def test_tts_reads_the_variant_stem(self) -> None:
        client = _FakeOpenAIClient()
        with patch("app.services.tts.get_openai_client", return_value=client):
            response = self.client.get(
                "/tts",
                params={"exam_id": "sample-exam", "question_number": 1, "variant": "true"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.speech_streaming.last_create_kwargs["input"], "Pick the bag with 4 apples.")

    def test_resolve_variant_dir_rejects_traversal(self) -> None:
        self.assertIsNone(resolve_variant_dir("../sample-exam", "q01"))
        self.assertIsNone(resolve_variant_dir("sample-exam", "../q01"))


if __name__ == "__main__":
    unittest.main()
