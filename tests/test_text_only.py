from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.text_only import (  # noqa: E402
    _choice_alignment_conflict,
    _normalize_text_quality,
    evaluate_text_only_blocking_errors,
)


class TextOnlyQualityTests(unittest.TestCase):
    def test_normalization_repairs_common_suffix_noise(self) -> None:
        clean, meta = _normalize_text_quality("9i", context="choice")
        self.assertEqual(clean, "9")
        self.assertGreaterEqual(meta["illegal_char_count"], 0)
        edit_types = {edit["type"] for edit in meta["normalization_edits"]}
        self.assertIn("strip_numeric_dangling_suffix", edit_types)

    def test_normalization_repairs_common_choice_ocr_confusion(self) -> None:
        clean, meta = _normalize_text_quality("A and Dl", context="choice")
        self.assertEqual(clean, "A and D")
        self.assertIn("Dl", meta["original_text"])

    def test_choice_alignment_conflict_detects_mismatch(self) -> None:
        choices_a = {"A": "1", "B": "2", "C": "3", "D": "4", "E": "5"}
        choices_b = {"A": "", "B": "", "C": "3", "D": "", "E": ""}
        self.assertTrue(_choice_alignment_conflict(choices_a, choices_b))

    def test_choice_alignment_conflict_not_triggered_on_match(self) -> None:
        choices_a = {"A": "cat", "B": "dog", "C": "fish", "D": "", "E": ""}
        choices_b = {"A": "cat", "B": "dog", "C": "fish", "D": "", "E": ""}
        self.assertFalse(_choice_alignment_conflict(choices_a, choices_b))

    def test_blocking_errors_flags_thresholds(self) -> None:
        payload = {
            "quality_summary": {
                "high_risk_question_count": 1,
                "option_alignment_conflict_count": 1,
                "max_illegal_char_ratio": 0.02,
            }
        }
        errors = evaluate_text_only_blocking_errors(
            payload,
            max_high_risk=0,
            max_option_alignment_conflict=0,
            max_illegal_char_ratio=0.0,
        )
        self.assertEqual(len(errors), 3)


if __name__ == "__main__":
    unittest.main()
