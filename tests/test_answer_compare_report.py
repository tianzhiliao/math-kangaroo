from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.answer_compare_report import build_answer_compare_report, validate_answer_compare_report
from kangaroo_pdf.pipeline import build_dataset
from kangaroo_pdf.workspace_paths import workspace_paths


class AnswerCompareReportTests(unittest.TestCase):
    def _write_pdf(self, path: Path, pages: list[dict[str, object]]) -> None:
        document = fitz.open()
        for index, page_spec in enumerate(pages, start=1):
            page = document.new_page(width=140, height=180)
            fill = tuple(page_spec["fill"])
            page.draw_rect(page.rect, color=fill, fill=fill)
            for line_number, line in enumerate(page_spec.get("lines", []), start=1):
                page.insert_text((12, 20 + (line_number * 14)), str(line), fontsize=11, color=(0, 0, 0))
        document.save(path.as_posix())
        document.close()

    def _pixel(self, path: Path) -> tuple[int, int, int]:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            return rgb.getpixel((rgb.width // 2, rgb.height // 2))

    def _build_sample_dataset(self, root: Path) -> tuple[Path, Path]:
        paths = workspace_paths(root)
        source_dir = paths.source_dir
        data_dir = paths.data_dir
        source_dir.mkdir(parents=True)
        (data_dir / "exams" / "canada-gr0102e-2026").mkdir(parents=True)
        (data_dir / "exams" / "felix-austria-2026").mkdir(parents=True)

        canada_pdf = source_dir / "2026gr0102e.pdf"
        felix_pdf = source_dir / "2026_Felix.pdf"
        answers_pdf = source_dir / "2026_Answers.pdf"

        self._write_pdf(
            canada_pdf,
            [
                {"fill": (1, 0, 0), "lines": ["Grade 1-2", "1. First", "2. Second"]},
                {"fill": (0, 0, 1), "lines": ["Answer key page"]},
            ],
        )
        self._write_pdf(
            felix_pdf,
            [
                {"fill": (1, 1, 1), "lines": ["1. (A) One", "2. (A) Two"]},
            ],
        )
        self._write_pdf(
            answers_pdf,
            [
                {"fill": (0, 1, 0), "lines": ["Felix B A"]},
                {"fill": (1, 1, 0), "lines": ["Unused second page"]},
            ],
        )

        manifest = {
            "generated_at": "2026-03-20T00:00:00+00:00",
            "exams": [
                {"exam_id": "canada-gr0102e-2026"},
                {"exam_id": "felix-austria-2026"},
            ],
        }
        (data_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        canada_exam = {
            "exam_id": "canada-gr0102e-2026",
            "source_pdf": canada_pdf.as_posix(),
            "question_count": 2,
            "questions": [
                {"number": 1, "answer": "A"},
                {"number": 2, "answer": "D"},
            ],
            "answer_key": {"1": "A", "2": "D"},
        }
        canada_audit = {
            "answer_source": {
                "document": canada_pdf.as_posix(),
                "method": "embedded_answer_page_underline",
                "mismatch_questions": [1],
                "raw_excerpt": "Canada answer page",
                "warnings": [],
            },
            "questions": [
                {"number": 1, "answer": "A", "answer_confidence": 1.0},
                {"number": 2, "answer": "D", "answer_confidence": 1.0},
            ],
        }
        felix_exam = {
            "exam_id": "felix-austria-2026",
            "source_pdf": felix_pdf.as_posix(),
            "question_count": 2,
            "questions": [
                {"number": 1, "answer": "B"},
                {"number": 2, "answer": "E"},
            ],
            "answer_key": {"1": "B", "2": "E"},
        }
        felix_audit = {
            "answer_source": {
                "document": answers_pdf.as_posix(),
                "method": "answer_table_text",
                "mismatch_questions": [2],
                "raw_excerpt": "Felix raw answer row",
                "warnings": [],
            },
            "questions": [
                {"number": 1, "answer": "B", "answer_confidence": 1.0},
                {"number": 2, "answer": "E", "answer_confidence": 1.0},
            ],
        }

        (data_dir / "exams" / "canada-gr0102e-2026" / "exam.json").write_text(
            json.dumps(canada_exam, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (data_dir / "exams" / "canada-gr0102e-2026" / "audit.json").write_text(
            json.dumps(canada_audit, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (data_dir / "exams" / "felix-austria-2026" / "exam.json").write_text(
            json.dumps(felix_exam, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (data_dir / "exams" / "felix-austria-2026" / "audit.json").write_text(
            json.dumps(felix_audit, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return source_dir, data_dir

    def test_build_report_uses_page_rules_and_raw_answers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir, data_dir = self._build_sample_dataset(root)
            report_dir = root / "reports" / "answer-compare"

            def fake_extract_answers(document, doc, answer_document):  # type: ignore[no-untyped-def]
                if document.filename == "2026gr0102e.pdf":
                    return {
                        "answers": {"1": "C", "2": "D"},
                        "method": "embedded_answer_page_underline",
                        "confidence_by_question": {"1": 0.61, "2": 0.42},
                        "page_by_question": {"1": 2, "2": 2},
                        "bbox_by_question": {},
                        "warnings": [],
                        "raw_excerpt": "Canada raw",
                    }
                return {
                    "answers": {"1": "B", "2": "A"},
                    "method": "answer_table_text",
                    "confidence_by_question": {"1": 0.9, "2": 0.9},
                    "page_by_question": {"1": 1, "2": 1},
                    "bbox_by_question": {},
                    "warnings": ["one warning"],
                    "raw_excerpt": "Felix raw",
                }

            with patch("kangaroo_pdf.answer_compare_report.extract_answers", side_effect=fake_extract_answers):
                manifest = build_answer_compare_report(source_dir, data_dir, report_dir)
                validation = validate_answer_compare_report(report_dir)

            self.assertEqual(manifest["exam_count"], 2)
            self.assertEqual(validation["exam_count"], 2)
            self.assertTrue((report_dir / "index.html").exists())

            canada_html = (report_dir / "canada-gr0102e-2026.html").read_text(encoding="utf-8")
            felix_html = (report_dir / "felix-austria-2026.html").read_text(encoding="utf-8")

            self.assertIn('src="assets/canada-gr0102e-2026/answer-page.png"', canada_html)
            self.assertNotIn('src="/', canada_html)
            self.assertNotIn("/Users/", canada_html)
            self.assertIn("class=\"answer-card mismatch\"", canada_html)
            self.assertIn("Q01", canada_html)
            self.assertIn(">C<", canada_html)
            self.assertIn(">A<", canada_html)
            self.assertIn("one warning", felix_html)
            self.assertIn("Mismatch", felix_html)
            self.assertIn(">A<", felix_html)
            self.assertIn(">E<", felix_html)

            canada_pixel = self._pixel(report_dir / "assets" / "canada-gr0102e-2026" / "answer-page.png")
            felix_pixel = self._pixel(report_dir / "assets" / "felix-austria-2026" / "answer-page.png")
            self.assertGreater(canada_pixel[2], 200)
            self.assertLess(canada_pixel[0], 60)
            self.assertGreater(felix_pixel[1], 200)
            self.assertLess(felix_pixel[0], 60)

    def test_repo_dataset_builds_all_exam_reports_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = workspace_paths(root)
            build_dataset(ROOT / "original_pdf_data", paths.data_dir)
            report_dir = paths.answer_compare_dir

            def fake_extract_answers(document, doc, answer_document):  # type: ignore[no-untyped-def]
                answers = {str(number): "A" for number in range(1, int(document.question_count or 0) + 1)}
                return {
                    "answers": answers,
                    "method": "embedded_answer_page_underline"
                    if "gr0102e" in document.filename
                    else "answer_table_text",
                    "confidence_by_question": {question: 0.9 for question in answers},
                    "page_by_question": {},
                    "bbox_by_question": {},
                    "warnings": [],
                    "raw_excerpt": "stubbed",
                }

            with patch("kangaroo_pdf.answer_compare_report.extract_answers", side_effect=fake_extract_answers):
                manifest = build_answer_compare_report(ROOT / "original_pdf_data", paths.data_dir, report_dir)
                validation = validate_answer_compare_report(report_dir)

            self.assertEqual(manifest["exam_count"], 16)
            self.assertEqual(validation["exam_count"], 16)
            self.assertTrue((report_dir / "index.html").exists())
            self.assertEqual(len(list(report_dir.glob("*.html"))), 17)


if __name__ == "__main__":
    unittest.main()
