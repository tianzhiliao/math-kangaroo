from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.pipeline import build_dataset
from kangaroo_pdf.review_tool import create_review_app


class ReviewToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_dir = ROOT / "original_pdf_data"
        cls.dataset_tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.dataset_tmp.name) / "data"
        build_dataset(cls.source_dir, cls.data_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.dataset_tmp.cleanup()

    def setUp(self) -> None:
        self.review_tmp = tempfile.TemporaryDirectory()
        review_dir = Path(self.review_tmp.name) / "review-data"
        self.client = TestClient(create_review_app(self.data_dir, review_dir))
        self.review_dir = review_dir

    def tearDown(self) -> None:
        self.client.close()
        self.review_tmp.cleanup()

    def test_lists_all_exams_and_initial_counts(self) -> None:
        response = self.client.get("/api/review/exams")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["counts"]["exams"], 16)
        self.assertEqual(payload["counts"]["total_questions"], 270)
        self.assertEqual(payload["counts"]["reviewed"], 0)
        self.assertEqual(len(payload["exams"]), 16)
        self.assertTrue(all(item["counts"]["unreviewed"] == item["question_count"] for item in payload["exams"]))

    def test_saves_review_and_restores_after_refresh(self) -> None:
        save_response = self.client.put(
            "/api/review/exams/canada-gr0102e-2020/questions/2",
            json={
                "status": "failed",
                "issue_types": ["missing_asset", "crop_region"],
                "affected_areas": ["stem", "reference_crop"],
                "note": "题图裁切不完整，且素材缺失。",
            },
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(save_response.json()["question"]["status"], "failed")

        detail_response = self.client.get("/api/review/exams/canada-gr0102e-2020")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()

        question_two = next(item for item in detail["question_views"] if item["number"] == 2)
        self.assertEqual(question_two["review"]["status"], "failed")
        self.assertEqual(question_two["review"]["issue_types"], ["missing_asset", "crop_region"])
        self.assertIn("题图裁切不完整", question_two["review"]["note"])

        review_file = self.review_dir / "canada-gr0102e-2020.json"
        self.assertTrue(review_file.exists())
        review_payload = json.loads(review_file.read_text(encoding="utf-8"))
        self.assertEqual(review_payload["counts"]["failed"], 1)

    def test_rejects_failed_without_issue_types(self) -> None:
        response = self.client.put(
            "/api/review/exams/canada-gr0102e-2020/questions/1",
            json={
                "status": "failed",
                "issue_types": [],
                "affected_areas": ["whole_question"],
                "note": "缺少分类",
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("issue_types", response.text)

    def test_builds_repair_backlog_from_saved_reviews(self) -> None:
        self.client.put(
            "/api/review/exams/felix-austria-2025/questions/1",
            json={
                "status": "follow_up",
                "issue_types": ["layout_render_error"],
                "affected_areas": ["whole_question"],
                "note": "渲染布局需要二次确认。",
            },
        )
        self.client.put(
            "/api/review/exams/felix-austria-2025/questions/2",
            json={
                "status": "failed",
                "issue_types": ["choice_text_error", "answer_key_error"],
                "affected_areas": ["choices", "answer"],
                "note": "选项和答案都需要核对。",
            },
        )

        response = self.client.get("/api/review/repair-backlog")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_items"], 2)

        exam_group = next(item for item in payload["exams"] if item["exam_id"] == "felix-austria-2025")
        self.assertEqual(len(exam_group["items"]), 2)
        self.assertEqual(exam_group["items"][0]["status"], "follow_up")
        self.assertEqual(exam_group["items"][1]["status"], "failed")

    def test_rebuild_dataset_does_not_touch_review_files(self) -> None:
        review_path = self.review_dir / "canada-gr0102e-2021.json"
        self.client.put(
            "/api/review/exams/canada-gr0102e-2021/questions/3",
            json={
                "status": "failed",
                "issue_types": ["wrong_asset"],
                "affected_areas": ["choices"],
                "note": "素材映射不正确。",
            },
        )
        original_content = review_path.read_text(encoding="utf-8")

        build_dataset(self.source_dir, self.data_dir)

        self.assertTrue(review_path.exists())
        self.assertEqual(review_path.read_text(encoding="utf-8"), original_content)

    def test_review_pages_render_shell(self) -> None:
        dashboard_response = self.client.get("/review")
        exam_response = self.client.get("/review/canada-gr0102e-2020")
        queue_response = self.client.get("/review/queue/failures")

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(exam_response.status_code, 200)
        self.assertEqual(queue_response.status_code, 200)

        self.assertIn("/review-static/review.js", dashboard_response.text)
        self.assertIn("/review-static/review.css", exam_response.text)
        self.assertIn("review-bootstrap", queue_response.text)


if __name__ == "__main__":
    unittest.main()
