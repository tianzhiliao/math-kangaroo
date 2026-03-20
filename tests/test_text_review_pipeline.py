from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.pipeline import build_dataset
from kangaroo_pdf.text_review_pipeline import (
    _clean_question_text,
    _classify_expected_mode,
    _review_priority,
    build_text_review_dataset,
    validate_text_review_dataset,
)
from kangaroo_pdf.workspace_paths import workspace_paths


class TextReviewPipelineTests(unittest.TestCase):
    def test_clean_question_text_removes_footer_noise(self) -> None:
        raw = """
        5. What piece completes the picture?
        (A)
        (B)
        Copyright 2020 All rights reserved.
        Do not duplicate or distribute without written permission from CMKC!
        """
        cleaned = _clean_question_text(raw)
        self.assertNotIn("Copyright", cleaned)
        self.assertNotIn("Do not duplicate", cleaned)
        self.assertIn("What piece completes the picture?", cleaned)

    def test_clean_question_text_stops_at_section_break(self) -> None:
        raw = """
        5. Put the animals in order of size.
        (A) 1
        (B) 2
        (C) 3
        (D) 4
        (E) 5
        - 4 Point Questions -
        1
        2
        3
        """
        cleaned = _clean_question_text(raw)
        self.assertNotIn("Point Questions", cleaned)
        self.assertTrue(cleaned.strip().endswith("(E) 5"))

    def test_classify_expected_mode_marks_visual_sequences_as_image_only(self) -> None:
        self.assertEqual(_classify_expected_mode("choice", "1 2 2 2", ["asset_1"]), "image_only")
        self.assertEqual(_classify_expected_mode("choice", "", ["asset_1"]), "image_only")
        self.assertEqual(_classify_expected_mode("choice", "Person A", ["asset_1"]), "text_with_image")
        self.assertEqual(_classify_expected_mode("choice", "5", []), "text_required")

    def test_review_priority_prefers_suspicious_and_image_only(self) -> None:
        self.assertEqual(
            _review_priority(
                baseline_text="old",
                extracted_text="new",
                expected_mode="text_required",
                suspicious=True,
            ),
            "suspicious",
        )
        self.assertEqual(
            _review_priority(
                baseline_text="",
                extracted_text="",
                expected_mode="image_only",
                suspicious=False,
            ),
            "image_only",
        )
        self.assertEqual(
            _review_priority(
                baseline_text="same",
                extracted_text="same",
                expected_mode="text_required",
                suspicious=False,
            ),
            "unchanged",
        )
        self.assertEqual(
            _review_priority(
                baseline_text="old",
                extracted_text="new",
                expected_mode="text_required",
                suspicious=False,
            ),
            "changed",
        )

    def test_build_text_review_dataset_fixes_known_bad_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = workspace_paths(root)
            build_dataset(ROOT / "original_pdf_data", paths.data_dir)

            output_dir = paths.review_dir
            report_dir = paths.text_report_dir
            manifest = build_text_review_dataset(
                source_dir=ROOT / "original_pdf_data",
                data_dir=paths.data_dir,
                output_dir=output_dir,
                report_dir=report_dir,
                exam_ids=["canada-gr0102e-2020", "canada-gr0102e-2021", "felix-austria-2014"],
            )
            validation = validate_text_review_dataset(output_dir, report_dir)

            self.assertEqual(validation["exam_count"], 3)
            self.assertEqual(len(manifest["exams"]), 3)

            canada_2020 = json.loads((output_dir / "canada-gr0102e-2020.json").read_text(encoding="utf-8"))
            fields = {field["field_id"]: field for field in canada_2020["fields"]}
            self.assertEqual(canada_2020["field_count"], 126)
            self.assertEqual(fields["q05.stem"]["extracted_text"], "What piece completes the picture?")
            self.assertEqual(fields["q10.stem"]["review_priority"], "changed")
            self.assertEqual(fields["q14.stem"]["review_priority"], "changed")
            self.assertEqual(fields["q18.choice.E"]["expected_mode"], "image_only")
            self.assertEqual(fields["q18.choice.E"]["extracted_text"], "")
            self.assertEqual(fields["q01.answer"]["baseline_text"], "D")
            self.assertEqual(fields["q01.answer"]["extracted_text"], "D")
            self.assertEqual(fields["q01.answer"]["review_status"], "pending")
            self.assertIn("review_notes", fields["q01.answer"])
            self.assertIn("reviewed_at", fields["q01.answer"])

            canada_2021 = json.loads((output_dir / "canada-gr0102e-2021.json").read_text(encoding="utf-8"))
            fields_2021 = {field["field_id"]: field for field in canada_2021["fields"]}
            self.assertEqual(fields_2021["q14.choice.E"]["expected_mode"], "image_only")
            self.assertEqual(fields_2021["q14.choice.E"]["extracted_text"], "")

            felix_2014 = json.loads((output_dir / "felix-austria-2014.json").read_text(encoding="utf-8"))
            fields_felix = {field["field_id"]: field for field in felix_2014["fields"]}
            self.assertEqual(fields_felix["q05.choice.E"]["extracted_text"], "5")
            self.assertEqual(fields_felix["q05.choice.E"]["review_priority"], "changed")

            self.assertTrue((report_dir / "index.html").exists())
            self.assertTrue((report_dir / "canada-gr0102e-2020.html").exists())


if __name__ == "__main__":
    unittest.main()
