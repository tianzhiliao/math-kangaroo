from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.report_page import build_report_page


class ReportPageTests(unittest.TestCase):
    def test_builds_single_file_report_with_real_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "codex-work-summary.html"
            report_data = build_report_page(ROOT / "data", output_path)
            self.assertTrue(output_path.exists())

            html = output_path.read_text(encoding="utf-8")
            self.assertIn("PDF 结构化成果说明", html)
            self.assertIn("我具体做了哪些事", html)
            self.assertIn("现在产出了哪些成果", html)
            self.assertIn("如果你想点开看，先看这几样", html)
            self.assertIn("一个真实例子", html)
            self.assertIn("28", html)
            self.assertIn("16", html)
            self.assertIn("canada-gr0102e-2020", html)
            self.assertIn("type=\"application/json\"", html)
            self.assertNotIn("fetch(", html)
            self.assertEqual(report_data["metrics"][0]["value"], "28")


if __name__ == "__main__":
    unittest.main()
