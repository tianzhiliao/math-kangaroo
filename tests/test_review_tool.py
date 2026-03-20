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

    def _completed_crop_payload(self, exam_id: str, question_number: int) -> dict[str, object]:
        detail = self.client.get(f"/api/crop-review/exams/{exam_id}").json()
        question = next(item for item in detail["question_views"] if item["number"] == question_number)
        return {
            "status": "completed",
            "stem_regions": [
                {
                    "page": region["page"],
                    "bbox": region["bbox"],
                    "order": region["order"],
                    "seed_asset_id": region.get("seed_asset_id"),
                }
                for region in question["seed_regions"]["stem"]
            ],
            "option_regions": {
                label: [
                    {
                        "page": region["page"],
                        "bbox": region["bbox"],
                        "order": region["order"],
                        "seed_asset_id": region.get("seed_asset_id"),
                    }
                    for region in question["seed_regions"]["options"][label]
                ]
                for label in ("A", "B", "C", "D", "E")
            },
        }

    def test_lists_all_exams_and_initial_counts(self) -> None:
        response = self.client.get("/api/review/exams")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["counts"]["exams"], 16)
        self.assertEqual(payload["counts"]["total_questions"], 270)
        self.assertEqual(payload["counts"]["reviewed"], 0)
        self.assertEqual(len(payload["exams"]), 16)
        self.assertTrue(all(item["counts"]["unreviewed"] == item["question_count"] for item in payload["exams"]))

    def test_crop_review_lists_exams_and_initial_counts(self) -> None:
        response = self.client.get("/api/crop-review/exams")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["counts"]["exams"], 16)
        self.assertEqual(payload["counts"]["ready"], 0)
        self.assertEqual(len(payload["exams"]), 16)
        canada_2020 = next(item for item in payload["exams"] if item["exam_id"] == "canada-gr0102e-2020")
        self.assertGreater(canada_2020["likely_visual_questions"], 0)

    def test_crop_review_detail_returns_seed_regions_and_page_cache(self) -> None:
        response = self.client.get("/api/crop-review/exams/canada-gr0102e-2020")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        question_two = next(item for item in payload["question_views"] if item["number"] == 2)
        self.assertTrue(question_two["seed_regions"]["stem"])
        self.assertEqual(sorted(question_two["seed_regions"]["options"].keys()), ["A", "B", "C", "D", "E"])
        self.assertEqual(question_two["effective_assets"]["mode"], "automatic")

        page_cache_path = self.review_dir / "page-cache" / "canada-gr0102e-2020" / "page-2.png"
        self.assertTrue(page_cache_path.exists())

    def test_crop_review_save_exports_manual_assets_and_overrides_contract(self) -> None:
        save_response = self.client.put(
            "/api/crop-review/exams/canada-gr0102e-2020/questions/2",
            json=self._completed_crop_payload("canada-gr0102e-2020", 2),
        )
        self.assertEqual(save_response.status_code, 200)

        payload = save_response.json()
        self.assertEqual(payload["question"]["manual"]["status"], "completed")
        self.assertEqual(payload["question"]["effective_assets"]["mode"], "manual_override")
        self.assertTrue(payload["question"]["effective_assets"]["agent_ready"])

        manual_doc_path = self.review_dir / "manual-crops" / "canada-gr0102e-2020.json"
        self.assertTrue(manual_doc_path.exists())
        manual_doc = json.loads(manual_doc_path.read_text(encoding="utf-8"))
        stem_export = manual_doc["questions"]["2"]["resolved_exports"]["stem"][0]
        self.assertTrue(Path(stem_export["absolute_path"]).exists())

        detail_response = self.client.get("/api/crop-review/exams/canada-gr0102e-2020")
        self.assertEqual(detail_response.status_code, 200)
        question_two = next(item for item in detail_response.json()["question_views"] if item["number"] == 2)
        self.assertEqual(question_two["effective_assets"]["mode"], "manual_override")

    def test_crop_review_rejects_incomplete_completed_payload(self) -> None:
        response = self.client.put(
            "/api/crop-review/exams/canada-gr0102e-2020/questions/2",
            json={
                "status": "completed",
                "stem_regions": [],
                "option_regions": {},
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("full A-E option_regions snapshot", response.text)

    def test_crop_review_rejects_non_empty_confirmed_no_visual(self) -> None:
        response = self.client.put(
            "/api/crop-review/exams/canada-gr0102e-2020/questions/1",
            json={
                "status": "confirmed_no_visual",
                "stem_regions": [
                    {
                        "page": 2,
                        "bbox": [395.8, 168.41, 562.5, 265.36],
                        "order": 1,
                        "seed_asset_id": "q01_stem_01",
                    }
                ],
                "option_regions": {label: [] for label in ("A", "B", "C", "D", "E")},
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("must save empty arrays", response.text)

    def test_crop_review_marks_saved_question_stale_when_source_changes(self) -> None:
        self.client.put(
            "/api/crop-review/exams/canada-gr0102e-2020/questions/2",
            json=self._completed_crop_payload("canada-gr0102e-2020", 2),
        )

        exam_path = self.data_dir / "exams" / "canada-gr0102e-2020" / "exam.json"
        original_text = exam_path.read_text(encoding="utf-8")
        try:
            exam_path.write_text(original_text + " \n", encoding="utf-8")
            detail_response = self.client.get("/api/crop-review/exams/canada-gr0102e-2020")
            self.assertEqual(detail_response.status_code, 200)
            payload = detail_response.json()
            question_two = next(item for item in payload["question_views"] if item["number"] == 2)
            self.assertTrue(question_two["manual"]["stale"])
            self.assertGreater(payload["meta"]["stale_question_count"], 0)
        finally:
            exam_path.write_text(original_text, encoding="utf-8")

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
        crop_path = self.review_dir / "manual-crops" / "canada-gr0102e-2020.json"
        self.client.put(
            "/api/review/exams/canada-gr0102e-2021/questions/3",
            json={
                "status": "failed",
                "issue_types": ["wrong_asset"],
                "affected_areas": ["choices"],
                "note": "素材映射不正确。",
            },
        )
        crop_response = self.client.put(
            "/api/crop-review/exams/canada-gr0102e-2020/questions/2",
            json=self._completed_crop_payload("canada-gr0102e-2020", 2),
        )
        self.assertEqual(crop_response.status_code, 200)
        original_content = review_path.read_text(encoding="utf-8")
        original_crop_content = crop_path.read_text(encoding="utf-8")

        build_dataset(self.source_dir, self.data_dir)

        self.assertTrue(review_path.exists())
        self.assertEqual(review_path.read_text(encoding="utf-8"), original_content)
        self.assertTrue(crop_path.exists())
        self.assertEqual(crop_path.read_text(encoding="utf-8"), original_crop_content)

    def test_review_pages_render_shell(self) -> None:
        dashboard_response = self.client.get("/review")
        exam_response = self.client.get("/review/canada-gr0102e-2020")
        queue_response = self.client.get("/review/queue/failures")
        crop_dashboard_response = self.client.get("/crop-review")
        crop_exam_response = self.client.get("/crop-review/canada-gr0102e-2020")

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(exam_response.status_code, 200)
        self.assertEqual(queue_response.status_code, 200)
        self.assertEqual(crop_dashboard_response.status_code, 200)
        self.assertEqual(crop_exam_response.status_code, 200)

        self.assertIn("/review-static/review.js", dashboard_response.text)
        self.assertIn("/review-static/review.css", exam_response.text)
        self.assertIn("review-bootstrap", queue_response.text)
        self.assertIn("/review-static/crop_review.js", crop_dashboard_response.text)
        self.assertIn("crop-review-bootstrap", crop_exam_response.text)


if __name__ == "__main__":
    unittest.main()
