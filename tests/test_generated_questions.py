from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.generated_questions import (
    ERROR,
    audit_generated_questions,
    render_markdown,
    resolve_variant_dir,
)

PNG_1600 = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (1600).to_bytes(4, "big") + (800).to_bytes(4, "big")
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><rect width="10" height="10" fill="#ACD0EC"/></svg>'


class CheckedInGeneratedQuestionsTests(unittest.TestCase):
    """The checked-in variants must be usable by the web app and the API."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit_generated_questions(ROOT / "release-data", ROOT / "generated")

    def test_every_release_question_has_a_variant(self) -> None:
        self.assertEqual(self.report.missing, [])
        self.assertEqual(
            self.report.variants + self.report.duplicates + len(self.report.withdrawn),
            self.report.source_questions,
        )

    def test_withdrawn_variants_are_not_served(self) -> None:
        for key, reason in self.report.withdrawn.items():
            exam_id, question_id = key.split("/")
            with self.subTest(variant=key):
                self.assertTrue(reason)
                self.assertIsNone(resolve_variant_dir(ROOT / "generated", exam_id, question_id))

    def test_no_audit_errors(self) -> None:
        errors = [f"{f.exam_id}/{f.question_id} {f.code}: {f.message}" for f in self.report.errors]
        self.assertEqual(errors, [])

    def test_no_audit_warnings(self) -> None:
        warnings = [f"{f.exam_id}/{f.question_id} {f.code}: {f.message}" for f in self.report.warnings]
        self.assertEqual(warnings, [])

    def test_duplicates_resolve_to_a_variant(self) -> None:
        for manifest_path in (ROOT / "generated").glob("*/manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest["questions"]:
                if entry.get("status") == "skipped-duplicate":
                    with self.subTest(exam=manifest["exam_id"], question=entry["id"]):
                        self.assertIsNotNone(
                            resolve_variant_dir(ROOT / "generated", manifest["exam_id"], entry["id"])
                        )


class AuditRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        root = Path(self._temp.name)
        self.release = root / "release-data"
        self.generated = root / "generated"
        exam_dir = self.release / "exams" / "ex"
        exam_dir.mkdir(parents=True)
        (self.release / "manifest.json").write_text(
            json.dumps({"exams": [{"exam_id": "ex", "path": "exams/ex/exam.json"}]}), encoding="utf-8"
        )
        self.source = {
            "id": "q01",
            "number": 1,
            "points": 3,
            "stem_text": "How many apples are in the basket?",
            "shared_asset_refs": ["q01_stem_01"],
            "choices": [{"label": l, "text": t, "asset_refs": []} for l, t in zip("ABCDE", "12345")],
        }
        (exam_dir / "exam.json").write_text(
            json.dumps({"exam_id": "ex", "answer_key": {"1": "B"}, "questions": [self.source]}),
            encoding="utf-8",
        )
        self.folder = self.generated / "ex" / "q01"
        self.folder.mkdir(parents=True)
        self.variant = {
            "id": "q01",
            "number": 1,
            "part": "part_a",
            "points": 3,
            "stem_text": "How many pears are on the plate?",
            "answer": "D",
            "choices": [{"label": l, "text": t, "asset_refs": []} for l, t in zip("ABCDE", "23456")],
            "shared_asset_refs": ["q01_stem_01"],
            "assets": [
                {
                    "id": "q01_stem_01",
                    "path": "figure.svg",
                    "format": "svg",
                    "media_type": "image/svg+xml",
                    "kind": "question_figure",
                    "role": "stem",
                    "width": 200,
                    "height": 100,
                }
            ],
        }
        (self.folder / "figure.svg").write_text(SVG, encoding="utf-8")
        (self.folder / "card.png").write_bytes(PNG_1600)
        (self.folder / "compare.png").write_bytes(PNG_1600)
        self._write_manifest({"id": "q01", "status": "generated", "answer": "D"})

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _write_manifest(self, *entries: dict) -> None:
        (self.generated / "ex" / "manifest.json").write_text(
            json.dumps({"exam_id": "ex", "questions": list(entries)}), encoding="utf-8"
        )

    def _codes(self, **changes) -> set[str]:
        (self.folder / "question.json").write_text(json.dumps({**self.variant, **changes}), encoding="utf-8")
        report = audit_generated_questions(self.release, self.generated)
        return {f.code for f in report.findings}

    def test_clean_variant_has_no_findings(self) -> None:
        self.assertEqual(self._codes(), set())

    def test_answer_must_be_a_choice(self) -> None:
        self.assertIn("answer_not_a_choice", self._codes(answer="F"))

    def test_answer_must_match_manifest(self) -> None:
        self.assertIn("manifest_answer_mismatch", self._codes(answer="C"))

    def test_duplicate_choice_texts(self) -> None:
        choices = [{"label": l, "text": "7", "asset_refs": []} for l in "ABCDE"]
        self.assertIn("choice_texts_duplicate", self._codes(choices=choices))

    def test_letter_only_choices_need_a_figure(self) -> None:
        choices = [{"label": l, "text": "", "asset_refs": []} for l in "ABCDE"]
        self.assertNotIn("choice_empty", self._codes(choices=choices))
        self.assertIn("choice_empty", self._codes(choices=choices, shared_asset_refs=[]))

    def test_unreferenced_figure_is_flagged(self) -> None:
        codes = self._codes(shared_asset_refs=[])
        self.assertIn("asset_unused", codes)
        self.assertIn("figure_dropped", codes)

    def test_unknown_asset_ref(self) -> None:
        self.assertIn("asset_ref_unknown", self._codes(shared_asset_refs=["nope"]))

    def test_non_english_text(self) -> None:
        self.assertIn("language", self._codes(stem_text="篮子里有几个苹果？"))

    def test_copy_of_source(self) -> None:
        self._write_manifest({"id": "q01", "status": "generated", "answer": "B"})
        codes = self._codes(stem_text=self.source["stem_text"], choices=self.source["choices"], answer="B")
        self.assertIn("copy_of_source", codes)

    def test_svg_with_raster_image(self) -> None:
        (self.folder / "figure.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><image href="data:image/png;base64,AA"/></svg>',
            encoding="utf-8",
        )
        self.assertIn("svg_embedded_image", self._codes())

    def test_broken_svg(self) -> None:
        (self.folder / "figure.svg").write_text("<svg", encoding="utf-8")
        self.assertIn("svg_invalid", self._codes())

    def test_missing_card(self) -> None:
        (self.folder / "card.png").unlink()
        self.assertIn("file_missing", self._codes())

    def test_withdrawn_variant_is_skipped_and_needs_a_reason(self) -> None:
        (self.folder / "question.json").write_text(json.dumps({**self.variant, "answer": "F"}), encoding="utf-8")
        self._write_manifest({"id": "q01", "status": "withdrawn", "answer": "F"})
        report = audit_generated_questions(self.release, self.generated)
        self.assertEqual(report.withdrawn, {"ex/q01": ""})
        self.assertEqual({f.code for f in report.findings}, {"withdrawn_without_reason"})
        self.assertIsNone(resolve_variant_dir(self.generated, "ex", "q01"))

        self._write_manifest({"id": "q01", "status": "withdrawn", "withdrawn_reason": "Two answers.", "answer": "F"})
        report = audit_generated_questions(self.release, self.generated)
        self.assertEqual(report.findings, [])
        self.assertEqual(report.variants, 0)

    def test_missing_variant(self) -> None:
        shutil.rmtree(self.folder)
        report = audit_generated_questions(self.release, self.generated)
        self.assertEqual(report.missing, ["ex/q01"])
        self.assertEqual(report.errors[0].severity, ERROR)

    def test_markdown_report_lists_findings(self) -> None:
        (self.folder / "question.json").write_text(json.dumps({**self.variant, "answer": "F"}), encoding="utf-8")
        report = audit_generated_questions(self.release, self.generated)
        text = render_markdown(
            report,
            {
                "model": "test-model",
                "results": [
                    {"exam_id": "ex", "question_id": "q01", "status": "disagree", "answer": "D", "model_answer": "C", "reasoning": "x"}
                ],
            },
        )
        self.assertIn("answer_not_a_choice", text)
        self.assertIn("Disagrees with the key: 1", text)


if __name__ == "__main__":
    unittest.main()
