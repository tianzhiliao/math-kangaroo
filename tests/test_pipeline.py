from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.pipeline import SUPPORTED_FAMILIES, build_dataset, classify_documents
from kangaroo_pdf.verified_answers import load_verified_answer_keys, verified_answer_key_ref


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_dir = ROOT / "original_pdf_data"

    def test_classifies_all_pdfs(self) -> None:
        documents = classify_documents(self.source_dir)
        self.assertEqual(len(documents), 28)
        for document in documents:
            self.assertIn(document.family, SUPPORTED_FAMILIES)

    def test_matches_golden_documents(self) -> None:
        documents = {document.filename: document for document in classify_documents(self.source_dir)}
        golden = json.loads((ROOT / "tests" / "fixtures" / "golden_documents.json").read_text(encoding="utf-8"))
        for expected in golden:
            document = documents[expected["filename"]]
            self.assertEqual(document.family, expected["family"])
            if "question_count" in expected:
                self.assertEqual(document.question_count, expected["question_count"])
            if "answer_mode" in expected:
                self.assertEqual(document.answer_mode, expected["answer_mode"])

    def test_builds_dataset_and_core_exam_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "data"
            manifest = build_dataset(self.source_dir, output_dir)
            verified_answer_keys = load_verified_answer_keys()
            self.assertTrue((output_dir / "manifest.json").exists())
            self.assertEqual(len(manifest["source_documents"]), 28)
            self.assertTrue(Path(manifest["qa_index_ref"]).exists())
            self.assertEqual({entry["exam_id"] for entry in manifest["exams"]}, set(verified_answer_keys))

            checks = {
                "canada-gr0102e-2023": {"family": "canada_gr0102e_18", "question_count": 18},
                "felix-austria-2014": {"family": "felix_austria_15", "question_count": 15},
                "felix-brazil-2020": {"family": "felix_brazil_24", "question_count": 24},
            }

            for exam_id, expected in checks.items():
                exam_path = output_dir / "exams" / exam_id / "exam.json"
                audit_path = output_dir / "exams" / exam_id / "audit.json"
                qa_path = Path(next(item for item in manifest["exams"] if item["exam_id"] == exam_id)["qa_review_ref"])
                self.assertTrue(exam_path.exists(), exam_id)
                self.assertTrue(audit_path.exists(), exam_id)
                self.assertTrue(qa_path.exists(), exam_id)
                exam = json.loads(exam_path.read_text(encoding="utf-8"))
                self.assertEqual(exam["family"], expected["family"])
                self.assertEqual(exam["question_count"], expected["question_count"])
                self.assertEqual(len(exam["questions"]), expected["question_count"])
                self.assertEqual(len(exam["answer_key"]), expected["question_count"])
                self.assertEqual(exam["answer_key"], verified_answer_keys[exam_id])
                self.assertIn("scoring_rules", exam)
                self.assertTrue(exam["source_audit_ref"].endswith("audit.json"))

                all_assets = {asset["id"]: asset for asset in exam["assets"]}
                referenced_asset_ids: set[str] = set()
                for question in exam["questions"]:
                    for asset_id in question["shared_asset_refs"]:
                        asset = all_assets[asset_id]
                        self.assertEqual(asset["role"], "stem")
                        self.assertTrue((output_dir / "exams" / exam_id / asset["path"]).exists())
                        referenced_asset_ids.add(asset_id)
                    for choice in question["choices"]:
                        for asset_id in choice["asset_refs"]:
                            asset = all_assets[asset_id]
                            self.assertEqual(asset["role"], "option")
                            self.assertTrue((output_dir / "exams" / exam_id / asset["path"]).exists())
                            referenced_asset_ids.add(asset_id)

                asset_dir = output_dir / "exams" / exam_id / "assets"
                expected_paths = {all_assets[asset_id]["path"] for asset_id in referenced_asset_ids}
                actual_paths = {
                    path.relative_to(output_dir / "exams" / exam_id).as_posix()
                    for path in asset_dir.iterdir()
                    if path.is_file()
                }
                self.assertEqual(actual_paths, expected_paths)
                self.assertTrue({asset["role"] for asset in exam["assets"]}.issubset({"stem", "option"}))

            canada_2023 = json.loads(
                (output_dir / "exams" / "canada-gr0102e-2023" / "exam.json").read_text(encoding="utf-8")
            )
            self.assertTrue(canada_2023["questions"][0]["shared_asset_refs"])
            self.assertEqual(
                sum(1 for choice in canada_2023["questions"][1]["choices"] if choice["asset_refs"]),
                5,
            )

            felix_2014 = json.loads(
                (output_dir / "exams" / "felix-austria-2014" / "exam.json").read_text(encoding="utf-8")
            )
            self.assertTrue(felix_2014["questions"][1]["shared_asset_refs"])
            self.assertEqual(
                sum(1 for choice in felix_2014["questions"][1]["choices"] if choice["asset_refs"]),
                5,
            )

            felix_2015 = json.loads(
                (output_dir / "exams" / "felix-austria-2015" / "exam.json").read_text(encoding="utf-8")
            )
            question_11 = felix_2015["questions"][10]
            self.assertFalse(question_11["shared_asset_refs"])
            self.assertFalse(any(choice["asset_refs"] for choice in question_11["choices"]))

            question_12 = felix_2015["questions"][11]
            self.assertTrue(question_12["shared_asset_refs"])
            self.assertFalse(any(choice["asset_refs"] for choice in question_12["choices"]))

            question_14 = felix_2015["questions"][13]
            self.assertFalse(question_14["shared_asset_refs"])
            self.assertFalse(any(choice["asset_refs"] for choice in question_14["choices"]))

            question_15 = felix_2015["questions"][14]
            self.assertFalse(question_15["shared_asset_refs"])
            self.assertFalse(any(choice["asset_refs"] for choice in question_15["choices"]))

            brazil_2020 = json.loads(
                (output_dir / "exams" / "felix-brazil-2020" / "exam.json").read_text(encoding="utf-8")
            )
            self.assertTrue(brazil_2020["questions"][2]["shared_asset_refs"])
            self.assertEqual(
                sum(1 for choice in brazil_2020["questions"][2]["choices"] if choice["asset_refs"]),
                5,
            )

            canada_2023_audit = json.loads(
                (output_dir / "exams" / "canada-gr0102e-2023" / "audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                canada_2023_audit["answer_source"]["document"],
                str((self.source_dir / "2023gr0102e.pdf").resolve()),
            )
            self.assertTrue(canada_2023_audit["answer_source"]["verified_against_source"])
            self.assertEqual(
                canada_2023_audit["answer_source"]["verified_answer_key_ref"],
                verified_answer_key_ref("canada-gr0102e-2023"),
            )
            self.assertEqual(canada_2023_audit["answer_source"]["mismatch_questions"], [])

            felix_2014_audit = json.loads(
                (output_dir / "exams" / "felix-austria-2014" / "audit.json").read_text(encoding="utf-8")
            )
            self.assertIn(1, felix_2014_audit["answer_source"]["mismatch_questions"])
            self.assertIn(15, felix_2014_audit["answer_source"]["mismatch_questions"])
            self.assertGreaterEqual(len(felix_2014_audit["answer_source"]["mismatch_questions"]), 5)


if __name__ == "__main__":
    unittest.main()
