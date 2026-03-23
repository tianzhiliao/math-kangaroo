"""Tests for kangaroo_pdf.ab_compare."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from kangaroo_pdf.ab_compare import AbCompareSide, ab_compare_paths_for_side, build_ab_manifest, default_ab_compare_roots


def _write_manifest(root: Path, exam_id: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps({"exams": [{"exam_id": exam_id}]}),
        encoding="utf-8",
    )


def _write_exam(root: Path, exam_id: str, stem: str, choice_a: str) -> None:
    exam_dir = root / "exams" / exam_id
    exam_dir.mkdir(parents=True)
    payload = {
        "exam_id": exam_id,
        "source_pdf": "/tmp/mock.pdf",
        "question_count": 1,
        "questions": [
            {
                "id": "q01",
                "number": 1,
                "part": "part_a",
                "points": 3,
                "stem_text": stem,
                "choices": [
                    {"label": "A", "text": choice_a, "asset_refs": []},
                    {"label": "B", "text": "b", "asset_refs": []},
                    {"label": "C", "text": "c", "asset_refs": []},
                    {"label": "D", "text": "d", "asset_refs": []},
                    {"label": "E", "text": "e", "asset_refs": []},
                ],
                "shared_asset_refs": [],
            }
        ],
    }
    (exam_dir / "exam.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_review(root: Path, exam_id: str) -> None:
    payload = {
        "schema_version": 2,
        "exam_id": exam_id,
        "fields": [
            {
                "field_id": "q01.stem",
                "question_number": 1,
                "kind": "stem",
                "review_priority": "unchanged",
                "review_status": "approved",
                "page": 1,
            },
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{exam_id}.json").write_text(json.dumps(payload), encoding="utf-8")


class TestAbCompare(unittest.TestCase):
    def test_build_ab_manifest_diff(self) -> None:
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        try:
            repo = tmp / "repo"
            repo.mkdir()
            a_root = repo / "a"
            b_root = repo / "b"
            _write_manifest(a_root, "exam-x")
            _write_manifest(b_root, "exam-x")
            _write_exam(a_root, "exam-x", stem="Hello", choice_a="1")
            _write_exam(b_root, "exam-x", stem="Hello", choice_a="2")
            _write_review(a_root / "rev", "exam-x")
            _write_review(b_root / "rev", "exam-x")

            m = build_ab_manifest(
                AbCompareSide("A", a_root, a_root / "rev"),
                AbCompareSide("B", b_root, b_root / "rev"),
                repo_root=repo,
            )
            self.assertEqual(m["exam_count"], 1)
            self.assertGreaterEqual(m["diff_count"], 1)
            stem_rows = [r for r in m["rows"] if r["field_id"] == "q01.stem"]
            self.assertEqual(len(stem_rows), 1)
            self.assertTrue(stem_rows[0]["same_raw"])
            choice_rows = [r for r in m["rows"] if r["field_id"] == "q01.choice.A"]
            self.assertEqual(len(choice_rows), 1)
            self.assertFalse(choice_rows[0]["same_raw"])
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)

    def test_ab_compare_paths_helpers(self) -> None:
        j, w = default_ab_compare_roots(Path("/tmp/r"))
        self.assertIn("ab-compare/jat", str(j))
        self.assertIn("ab-compare/wyo", str(w))
        d, r, _, _ = ab_compare_paths_for_side(Path("/tmp/r"), "jat")
        self.assertEqual(d.parent.name, "jat")
        self.assertIn("review-data", str(r))


if __name__ == "__main__":
    unittest.main()
