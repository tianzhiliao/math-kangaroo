from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from wsgiref.util import setup_testing_defaults

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.pipeline import build_dataset
from kangaroo_pdf.text_review_pipeline import build_text_review_dataset
from kangaroo_pdf.unified_review import create_unified_review_app
from kangaroo_pdf.workspace_paths import workspace_paths


def request_app(
    app,
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    raw_path, _, raw_query = path.partition("?")
    environ["REQUEST_METHOD"] = method.upper()
    environ["PATH_INFO"] = raw_path
    environ["QUERY_STRING"] = raw_query
    body = b""
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        environ["CONTENT_TYPE"] = "application/json"
    environ["CONTENT_LENGTH"] = str(len(body))
    environ["wsgi.input"] = BytesIO(body)

    response_meta: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]], exc_info=None) -> None:
        response_meta["status"] = status
        response_meta["headers"] = {key: value for key, value in headers}

    body_bytes = b"".join(app(environ, start_response))
    status_code = int(str(response_meta["status"]).split()[0])
    return status_code, dict(response_meta["headers"]), body_bytes


class UnifiedReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.paths = workspace_paths(cls.temp_dir.name)
        build_dataset(ROOT / "original_pdf_data", cls.paths.data_dir)
        build_text_review_dataset(
            source_dir=ROOT / "original_pdf_data",
            data_dir=cls.paths.data_dir,
            output_dir=cls.paths.review_dir,
            report_dir=cls.paths.text_report_dir,
            exam_ids=["canada-gr0102e-2020", "felix-austria-2025"],
        )

        # Emulate a pre-upgrade v1 sidecar so the unified review service must synthesize
        # answer fields and default human-review metadata at read time.
        canada_path = cls.paths.review_dir / "canada-gr0102e-2020.json"
        canada_payload = json.loads(canada_path.read_text(encoding="utf-8"))
        canada_payload["schema_version"] = 1
        canada_payload["fields"] = [field for field in canada_payload["fields"] if field["kind"] != "answer"]
        for field in canada_payload["fields"]:
            field.pop("review_status", None)
            field.pop("review_notes", None)
            field.pop("reviewed_at", None)
        canada_payload["field_count"] = len(canada_payload["fields"])
        canada_path.write_text(json.dumps(canada_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        cls.app = create_unified_review_app(
            data_dir=cls.paths.data_dir,
            review_dir=cls.paths.review_dir,
            release_dir=ROOT / "release-data",
            cache_dir=cls.paths.cache_dir,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_exam_api_synthesizes_answer_fields_for_old_sidecar(self) -> None:
        status, headers, body = request_app(type(self).app, "GET", "/api/exams/canada-gr0102e-2020")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")

        payload = json.loads(body.decode("utf-8"))
        q1 = next(question for question in payload["question_views"] if question["number"] == 1)
        field_ids = {field["field_id"] for field in q1["field_views"]}
        self.assertIn("q01.answer", field_ids)

        answer_field = next(field for field in q1["field_views"] if field["field_id"] == "q01.answer")
        self.assertEqual(answer_field["baseline_text"], "D")
        self.assertEqual(answer_field["extracted_text"], "D")
        self.assertEqual(answer_field["review_status"], "pending")

        status_felix, _, body_felix = request_app(type(self).app, "GET", "/api/exams/felix-austria-2025")
        self.assertEqual(status_felix, 200)
        felix_payload = json.loads(body_felix.decode("utf-8"))
        self.assertTrue(felix_payload["answer_source"]["method"].startswith("answer_table_"))

    def test_post_review_persists_field_status(self) -> None:
        status, _, body = request_app(
            type(self).app,
            "POST",
            "/api/exams/canada-gr0102e-2020/fields/q01.answer/review",
            payload={"review_status": "approved", "review_notes": "Answer confirmed against source."},
        )
        self.assertEqual(status, 200)
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["field"]["review_status"], "approved")
        self.assertEqual(payload["field"]["review_notes"], "Answer confirmed against source.")
        self.assertIsNotNone(payload["field"]["reviewed_at"])

        saved = json.loads((self.paths.review_dir / "canada-gr0102e-2020.json").read_text(encoding="utf-8"))
        saved_field = next(field for field in saved["fields"] if field["field_id"] == "q01.answer")
        self.assertEqual(saved_field["review_status"], "approved")
        self.assertEqual(saved_field["review_notes"], "Answer confirmed against source.")

    def test_html_and_artifact_routes_render(self) -> None:
        status_index, headers_index, body_index = request_app(type(self).app, "GET", "/")
        self.assertEqual(status_index, 200)
        self.assertEqual(headers_index["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Unified PDF / Text / Image Review", body_index.decode("utf-8"))

        status_exam, _, body_exam = request_app(type(self).app, "GET", "/exams/canada-gr0102e-2020")
        self.assertEqual(status_exam, 200)
        html_text = body_exam.decode("utf-8")
        self.assertIn("Original PDF Page", html_text)
        self.assertIn("Extracted Text Review", html_text)

        status_page, headers_page, body_page = request_app(
            type(self).app,
            "GET",
            "/artifacts/pages/canada-gr0102e-2020/2.png",
        )
        self.assertEqual(status_page, 200)
        self.assertEqual(headers_page["Content-Type"], "image/png")
        self.assertGreater(len(body_page), 1000)

        status_asset, headers_asset, body_asset = request_app(
            type(self).app,
            "GET",
            "/artifacts/assets/canada-gr0102e-2020/q01_stem_01",
        )
        self.assertEqual(status_asset, 200)
        self.assertEqual(headers_asset["Content-Type"], "image/png")
        self.assertGreater(len(body_asset), 100)


if __name__ == "__main__":
    unittest.main()
