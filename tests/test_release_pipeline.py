from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.release_pipeline import (
    ReleaseDataValidationError,
    build_cleanup_allowlist_report,
    build_release_dataset,
    validate_release_dataset,
)
from kangaroo_pdf.workspace_paths import workspace_paths


class ReleasePipelineTests(unittest.TestCase):
    def _make_source_dataset(self, root: Path) -> Path:
        data_dir = workspace_paths(root).data_dir
        exam_id = "sample-exam"
        exam_dir = data_dir / "exams" / exam_id
        manual_asset_dir = exam_dir / "assets" / "manual"
        manual_asset_dir.mkdir(parents=True, exist_ok=True)

        self._write_png(manual_asset_dir / "q01_stem_01.png", (80, 40), "black")
        self._write_png(manual_asset_dir / "q02_stem_01.png", (60, 32), "navy")

        exam_payload = {
            "exam_id": exam_id,
            "year": 2026,
            "family": "sample_family",
            "level": "sample",
            "language": "en",
            "duration_minutes": 45,
            "question_count": 1,
            "scoring_rules": [{"from": 1, "to": 1, "points": 3}],
            "instructions": ["Read carefully."],
            "assets": [
                {
                    "id": "q01_stem_01",
                    "path": "assets/manual/q01_stem_01.png",
                    "kind": "question_figure",
                    "format": "png",
                    "page": 1,
                    "bbox": [0, 0, 80, 40],
                    "role": "stem",
                    "source": "manual_crop",
                },
                {
                    "id": "q02_stem_01",
                    "path": "assets/manual/q02_stem_01.png",
                    "kind": "question_figure",
                    "format": "png",
                    "page": 1,
                    "bbox": [0, 0, 60, 32],
                    "role": "stem",
                    "source": "manual_crop",
                },
            ],
            "questions": [
                {
                    "id": "q01",
                    "number": 1,
                    "part": "part_a",
                    "points": 3,
                    "stem_text": "Which figure is shaded?",
                    "choices": [
                        {"label": "A", "text": "A", "asset_refs": [], "legacy_auto_asset_refs": []},
                        {"label": "B", "text": "B", "asset_refs": [], "legacy_auto_asset_refs": []},
                        {"label": "C", "text": "C", "asset_refs": [], "legacy_auto_asset_refs": []},
                        {"label": "D", "text": "D", "asset_refs": [], "legacy_auto_asset_refs": []},
                        {"label": "E", "text": "E", "asset_refs": [], "legacy_auto_asset_refs": []},
                    ],
                    "shared_asset_refs": ["q01_stem_01"],
                    "answer": "A",
                    "source": {"page": 1, "bbox": [0, 0, 80, 40]},
                    "legacy_auto_shared_asset_refs": ["q01_stem_01"],
                }
            ],
            "answer_key": {"1": "A"},
            "source_audit_ref": f"exams/{exam_id}/audit.json",
            "warnings": [],
            "legacy_auto_assets": [],
            "manual_crop_ref": f"review-data/manual-crops/{exam_id}.json",
            "asset_source": "manual_crops_applied",
        }
        manifest_payload = {
            "generated_at": "2026-03-19T00:00:00+00:00",
            "exams": [{"exam_id": exam_id}],
        }

        (data_dir / "manifest.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (exam_dir / "exam.json").write_text(
            json.dumps(exam_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return data_dir

    def _write_png(self, path: Path, size: tuple[int, int], fill: str) -> None:
        image = Image.new("RGB", size, "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, size[0] - 1, size[1] - 1), fill=fill)
        image.save(path)

    def test_builds_png_release_dataset_and_trims_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = self._make_source_dataset(root)
            output_dir = root / "release-data"

            manifest = build_release_dataset(data_dir, output_dir)
            validation = validate_release_dataset(output_dir)

            self.assertEqual(validation["exam_count"], 1)
            self.assertEqual(manifest["exams"][0]["asset_count"], 1)

            exam_payload = json.loads((output_dir / "exams" / "sample-exam" / "exam.json").read_text(encoding="utf-8"))
            asset = exam_payload["assets"][0]

            self.assertEqual(set(manifest.keys()), {"schema_version", "generated_at", "exams"})
            self.assertEqual(set(manifest["exams"][0].keys()), {"asset_count", "exam_id", "family", "language", "level", "path", "question_count", "year"})
            self.assertEqual(set(exam_payload.keys()), {"answer_key", "assets", "duration_minutes", "exam_id", "family", "instructions", "language", "level", "question_count", "questions", "scoring_rules", "year"})
            self.assertEqual(asset["format"], "png")
            self.assertEqual(asset["media_type"], "image/png")
            self.assertEqual(asset["width"], 80)
            self.assertEqual(asset["height"], 40)
            self.assertEqual(asset["path"], "assets/q01_stem_01.png")
            self.assertTrue((output_dir / "exams" / "sample-exam" / asset["path"]).exists())
            self.assertNotIn("source_pdf", exam_payload)
            self.assertNotIn("manual_crop_ref", exam_payload)
            self.assertNotIn("legacy_auto_assets", exam_payload)
            self.assertNotIn("answer", exam_payload["questions"][0])
            self.assertNotIn("source", exam_payload["questions"][0])
            self.assertNotIn("legacy_auto_shared_asset_refs", exam_payload["questions"][0])
            self.assertNotIn("legacy_auto_asset_refs", exam_payload["questions"][0]["choices"][0])

    def test_only_copies_referenced_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = self._make_source_dataset(root)
            output_dir = root / "release-data"

            build_release_dataset(data_dir, output_dir)
            exam_dir = output_dir / "exams" / "sample-exam"
            copied_files = sorted(path.name for path in (exam_dir / "assets").iterdir() if path.is_file())

            self.assertEqual(copied_files, ["q01_stem_01.png"])

    def test_build_cleanup_allowlist_report_lists_inputs_and_delete_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = self._make_source_dataset(root)
            generated_paths = workspace_paths(root)
            generated_paths.cache_dir.mkdir(parents=True, exist_ok=True)
            (generated_paths.cache_dir / "preview.png").write_text("cache\n", encoding="utf-8")
            (root / "review-data").mkdir()
            (root / "review-data" / "manual-crops.json").write_text("{}\n", encoding="utf-8")
            (root / "reports").mkdir()
            (root / "reports" / "index.html").write_text("<html></html>\n", encoding="utf-8")
            (root / "original_pdf_data").mkdir()
            (root / "original_pdf_data" / "sample.pdf").write_text("pdf\n", encoding="utf-8")
            (root / "release-data" / "exams" / "sample-exam").mkdir(parents=True, exist_ok=True)
            (root / "release-data" / "exams" / "sample-exam" / "exam.json").write_text("{}\n", encoding="utf-8")
            (root / "tmp").mkdir()
            (root / "tmp" / "cache.txt").write_text("cache\n", encoding="utf-8")

            report_path = root / "cleanup-report.json"
            report = build_cleanup_allowlist_report(data_dir, report_path)

            self.assertTrue(report_path.exists())
            input_paths = {item["path"] for item in report["release_input_files"]}
            delete_paths = {item["path"] for item in report["delete_candidates"]}
            self.assertIn(".generated/data/manifest.json", input_paths)
            self.assertIn(".generated/data/exams/sample-exam/exam.json", input_paths)
            self.assertIn(".generated/data/exams/sample-exam/assets/manual/q01_stem_01.png", input_paths)
            self.assertIn(".generated/data/manifest.json", delete_paths)
            self.assertIn(".generated/cache/preview.png", delete_paths)
            self.assertIn("review-data/manual-crops.json", delete_paths)
            self.assertIn("reports/index.html", delete_paths)
            self.assertIn("tmp/cache.txt", delete_paths)
            self.assertNotIn("original_pdf_data/sample.pdf", delete_paths)
            self.assertNotIn("release-data/exams/sample-exam/exam.json", delete_paths)

    def test_validate_release_dataset_rejects_legacy_field_leak(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = self._make_source_dataset(root)
            output_dir = root / "release-data"
            build_release_dataset(data_dir, output_dir)

            exam_path = output_dir / "exams" / "sample-exam" / "exam.json"
            exam_payload = json.loads(exam_path.read_text(encoding="utf-8"))
            exam_payload["source_pdf"] = "/tmp/source.pdf"
            exam_path.write_text(json.dumps(exam_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            with self.assertRaises(ReleaseDataValidationError):
                validate_release_dataset(output_dir)

    @unittest.skipUnless((ROOT / "release-data").exists(), "release-data has not been built yet")
    def test_repo_release_dataset_is_valid(self) -> None:
        validation = validate_release_dataset(ROOT / "release-data")
        self.assertEqual(validation["exam_count"], 16)


if __name__ == "__main__":
    unittest.main()
