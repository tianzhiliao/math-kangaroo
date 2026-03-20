from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.answer_sync import sync_rebuilt_answers
from kangaroo_pdf.workspace_paths import workspace_paths


class AnswerSyncTests(unittest.TestCase):
    def test_sync_rebuilt_answers_updates_only_answer_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rebuilt_dir = root / "rebuilt-data"
            paths = workspace_paths(root)
            data_dir = paths.data_dir
            release_dir = paths.release_dir
            review_dir = paths.review_dir

            (rebuilt_dir / "exams" / "sample-exam").mkdir(parents=True)
            (data_dir / "exams" / "sample-exam").mkdir(parents=True)
            (release_dir / "exams" / "sample-exam").mkdir(parents=True)
            review_dir.mkdir(parents=True)

            (rebuilt_dir / "manifest.json").write_text(
                json.dumps({"exams": [{"exam_id": "sample-exam"}]}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            current_exam = {
                "exam_id": "sample-exam",
                "questions": [
                    {"number": 1, "answer": "A", "stem_text": "one"},
                    {"number": 2, "answer": "B", "stem_text": "two"},
                ],
                "answer_key": {"1": "A", "2": "B"},
                "unchanged_field": "keep-me",
            }
            rebuilt_exam = {
                "exam_id": "sample-exam",
                "questions": [
                    {"number": 1, "answer": "C", "stem_text": "one"},
                    {"number": 2, "answer": "B", "stem_text": "two"},
                ],
                "answer_key": {"1": "C", "2": "B"},
                "unchanged_field": "different-temp-value",
            }
            current_audit = {
                "exam_id": "sample-exam",
                "answer_source": {"document": "old.pdf", "method": "old", "raw_excerpt": "", "warnings": []},
                "qa_review_ref": "/keep/me.html",
                "questions": [
                    {"number": 1, "answer": "A", "answer_confidence": 0.2, "text_bbox": [1, 2, 3, 4]},
                    {"number": 2, "answer": "B", "answer_confidence": 0.3, "text_bbox": [5, 6, 7, 8]},
                ],
            }
            rebuilt_audit = {
                "exam_id": "sample-exam",
                "answer_source": {
                    "document": "new.pdf",
                    "method": "verified",
                    "raw_excerpt": "excerpt",
                    "warnings": [],
                    "verified_against_source": True,
                    "verified_answer_key_ref": "verified.json#sample-exam",
                    "mismatch_questions": [1],
                },
                "qa_review_ref": "/tmp/should-not-win.html",
                "questions": [
                    {"number": 1, "answer": "C", "answer_confidence": 1.0, "text_bbox": [9, 9, 9, 9]},
                    {"number": 2, "answer": "B", "answer_confidence": 0.8, "text_bbox": [8, 8, 8, 8]},
                ],
            }
            current_release = {
                "exam_id": "sample-exam",
                "answer_key": {"1": "A", "2": "B"},
                "questions": [{"number": 1}],
            }
            current_review = {
                "schema_version": 2,
                "generated_at": "2026-03-20T00:00:00+00:00",
                "exam_id": "sample-exam",
                "source_pdf": "sample.pdf",
                "question_count": 2,
                "field_count": 3,
                "fields": [
                    {
                        "field_id": "q01.answer",
                        "question_number": 1,
                        "kind": "answer",
                        "choice_label": None,
                        "expected_mode": "text_required",
                        "baseline_text": "A",
                        "extracted_text": "A",
                        "verified_text": "",
                        "status": "pending",
                        "review_priority": "unchanged",
                        "method": "answer_table_ocr",
                        "confidence": 0.75,
                        "page": 1,
                        "text_bbox": [],
                        "asset_refs": [],
                        "review_status": "approved",
                        "review_notes": "confirmed",
                        "reviewed_at": "2026-03-20T00:00:00+00:00",
                    },
                    {
                        "field_id": "q02.answer",
                        "question_number": 2,
                        "kind": "answer",
                        "choice_label": None,
                        "expected_mode": "text_required",
                        "baseline_text": "B",
                        "extracted_text": "B",
                        "verified_text": "",
                        "status": "pending",
                        "review_priority": "unchanged",
                        "method": "answer_table_ocr",
                        "confidence": 0.75,
                        "page": 1,
                        "text_bbox": [],
                        "asset_refs": [],
                        "review_status": "approved",
                        "review_notes": "keep",
                        "reviewed_at": "2026-03-20T00:00:00+00:00",
                    },
                    {
                        "field_id": "q01.stem",
                        "question_number": 1,
                        "kind": "stem",
                        "choice_label": None,
                        "expected_mode": "text_required",
                        "baseline_text": "one",
                        "extracted_text": "one",
                        "verified_text": "",
                        "status": "pending",
                        "review_priority": "unchanged",
                        "method": "pymupdf_text",
                        "confidence": 1.0,
                        "page": 1,
                        "text_bbox": [],
                        "asset_refs": [],
                        "review_status": "approved",
                        "review_notes": "unchanged",
                        "reviewed_at": "2026-03-20T00:00:00+00:00",
                    },
                ],
            }
            replacement_fields = [
                {
                    "field_id": "q01.answer",
                    "question_number": 1,
                    "kind": "answer",
                    "choice_label": None,
                    "expected_mode": "text_required",
                    "baseline_text": "C",
                    "extracted_text": "C",
                    "verified_text": "",
                    "status": "pending",
                    "review_priority": "unchanged",
                    "method": "verified",
                    "confidence": 1.0,
                    "page": 1,
                    "text_bbox": [],
                    "asset_refs": [],
                    "review_status": "pending",
                    "review_notes": "",
                    "reviewed_at": None,
                },
                {
                    "field_id": "q02.answer",
                    "question_number": 2,
                    "kind": "answer",
                    "choice_label": None,
                    "expected_mode": "text_required",
                    "baseline_text": "B",
                    "extracted_text": "B",
                    "verified_text": "",
                    "status": "pending",
                    "review_priority": "unchanged",
                    "method": "verified",
                    "confidence": 1.0,
                    "page": 1,
                    "text_bbox": [],
                    "asset_refs": [],
                    "review_status": "pending",
                    "review_notes": "",
                    "reviewed_at": None,
                },
            ]

            (data_dir / "exams" / "sample-exam" / "exam.json").write_text(
                json.dumps(current_exam, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (rebuilt_dir / "exams" / "sample-exam" / "exam.json").write_text(
                json.dumps(rebuilt_exam, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (data_dir / "exams" / "sample-exam" / "audit.json").write_text(
                json.dumps(current_audit, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (rebuilt_dir / "exams" / "sample-exam" / "audit.json").write_text(
                json.dumps(rebuilt_audit, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (release_dir / "exams" / "sample-exam" / "exam.json").write_text(
                json.dumps(current_release, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (review_dir / "sample-exam.json").write_text(
                json.dumps(current_review, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            summary = sync_rebuilt_answers(
                rebuilt_data_dir=rebuilt_dir,
                data_dir=data_dir,
                release_dir=release_dir,
                review_dir=review_dir,
                answer_field_provider=lambda exam: replacement_fields,
            )

            synced_exam = json.loads((data_dir / "exams" / "sample-exam" / "exam.json").read_text(encoding="utf-8"))
            synced_audit = json.loads((data_dir / "exams" / "sample-exam" / "audit.json").read_text(encoding="utf-8"))
            synced_release = json.loads(
                (release_dir / "exams" / "sample-exam" / "exam.json").read_text(encoding="utf-8")
            )
            synced_review = json.loads((review_dir / "sample-exam.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["exam_count"], 1)
            self.assertEqual(summary["exams"][0]["changed_questions"], [1])
            self.assertEqual(summary["exams"][0]["review_field_ids_reset"], ["q01.answer"])

            self.assertEqual(synced_exam["answer_key"], {"1": "C", "2": "B"})
            self.assertEqual(synced_exam["questions"][0]["answer"], "C")
            self.assertEqual(synced_exam["unchanged_field"], "keep-me")

            self.assertEqual(synced_audit["answer_source"], rebuilt_audit["answer_source"])
            self.assertEqual(synced_audit["qa_review_ref"], "/keep/me.html")
            self.assertEqual(synced_audit["questions"][0]["answer"], "C")
            self.assertEqual(synced_audit["questions"][0]["answer_confidence"], 1.0)
            self.assertEqual(synced_audit["questions"][0]["text_bbox"], [1, 2, 3, 4])

            self.assertEqual(synced_release["answer_key"], {"1": "C", "2": "B"})
            self.assertEqual(synced_release["questions"], [{"number": 1}])

            answer_field = next(field for field in synced_review["fields"] if field["field_id"] == "q01.answer")
            unchanged_answer_field = next(field for field in synced_review["fields"] if field["field_id"] == "q02.answer")
            stem_field = next(field for field in synced_review["fields"] if field["field_id"] == "q01.stem")
            self.assertEqual(answer_field["baseline_text"], "C")
            self.assertEqual(answer_field["review_status"], "pending")
            self.assertEqual(answer_field["review_notes"], "")
            self.assertIsNone(answer_field["reviewed_at"])
            self.assertEqual(unchanged_answer_field["review_status"], "approved")
            self.assertEqual(unchanged_answer_field["review_notes"], "keep")
            self.assertEqual(stem_field["review_notes"], "unchanged")

    def test_sync_rebuilt_answers_can_update_release_without_working_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rebuilt_dir = root / "rebuilt-data"
            release_dir = workspace_paths(root).release_dir

            (rebuilt_dir / "exams" / "sample-exam").mkdir(parents=True)
            (release_dir / "exams" / "sample-exam").mkdir(parents=True)

            (rebuilt_dir / "manifest.json").write_text(
                json.dumps({"exams": [{"exam_id": "sample-exam"}]}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (rebuilt_dir / "exams" / "sample-exam" / "exam.json").write_text(
                json.dumps(
                    {
                        "exam_id": "sample-exam",
                        "questions": [{"number": 1, "answer": "D"}],
                        "answer_key": {"1": "D"},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (rebuilt_dir / "exams" / "sample-exam" / "audit.json").write_text(
                json.dumps(
                    {
                        "exam_id": "sample-exam",
                        "answer_source": {"document": "new.pdf", "method": "verified", "raw_excerpt": "", "warnings": []},
                        "questions": [{"number": 1, "answer": "D", "answer_confidence": 1.0}],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (release_dir / "exams" / "sample-exam" / "exam.json").write_text(
                json.dumps(
                    {
                        "exam_id": "sample-exam",
                        "answer_key": {"1": "A"},
                        "questions": [{"number": 1}],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            summary = sync_rebuilt_answers(
                rebuilt_data_dir=rebuilt_dir,
                data_dir=None,
                release_dir=release_dir,
            )

            synced_release = json.loads(
                (release_dir / "exams" / "sample-exam" / "exam.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(summary["data_dir"])
            self.assertEqual(summary["exams"][0]["changed_questions"], [])
            self.assertFalse(summary["exams"][0]["exam_updated"])
            self.assertTrue(summary["exams"][0]["release_updated"])
            self.assertEqual(synced_release["answer_key"], {"1": "D"})


if __name__ == "__main__":
    unittest.main()
