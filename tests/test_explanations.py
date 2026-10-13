from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.explanations import (
    load_original_questions,
    load_variant_questions,
    question_content_hash,
    stamp_content_hashes,
    validate_exam,
)

EXAM_ID = "sample-exam"


def _choices(texts: list[str]) -> list[dict]:
    return [{"label": label, "text": text, "asset_refs": []} for label, text in zip("ABCDE", texts)]


def _entry(source: str, answer: str, labels: str = "ABCDE", **overrides) -> dict:
    entry = {
        "source": source,
        "content_hash": "",
        "answer": answer,
        "independent_answer": answer,
        "key_idea": "Count the stars one by one.",
        "steps": ["Point to each star and count.", "There are 4 stars."],
        "answer_sentence": f"So the answer is {answer}.",
        "choice_feedback": {label: f"{label} is too many or too few." for label in labels if label != answer},
        "generated_by": "test",
        "generated_at": "2026-10-12T00:00:00Z",
        "review": {"status": "unreviewed", "note": None},
    }
    entry.update(overrides)
    return entry


class ExplanationValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        root = Path(self._temp.name)
        self.release_dir = root / "release-data"
        self.generated_dir = root / "generated"

        exam_dir = self.release_dir / "exams" / EXAM_ID
        (exam_dir / "assets").mkdir(parents=True)
        (exam_dir / "assets" / "q01_stem_01.png").write_bytes(b"png-bytes")
        self._write(
            exam_dir / "exam.json",
            {
                "exam_id": EXAM_ID,
                "answer_key": {"1": "B", "2": "D"},
                "assets": [{"id": "q01_stem_01", "path": "assets/q01_stem_01.png"}],
                "questions": [
                    {
                        "id": "q01",
                        "number": 1,
                        "stem_text": "How many stars?",
                        "choices": _choices(["3", "4", "5", "6", "7"]),
                        "shared_asset_refs": ["q01_stem_01"],
                    },
                    {
                        "id": "q02",
                        "number": 2,
                        "stem_text": "Which shape is round?",
                        "choices": _choices(["square", "triangle", "star", "circle", "heart"]),
                        "shared_asset_refs": [],
                    },
                ],
            },
        )

        variant_dir = self.generated_dir / EXAM_ID / "q01"
        variant_dir.mkdir(parents=True)
        (variant_dir / "figure.svg").write_text("<svg/>", encoding="utf-8")
        self._write(
            variant_dir / "question.json",
            {
                "id": "q01",
                "number": 1,
                "stem_text": "How many moons?",
                "answer": "C",
                "choices": _choices(["1", "2", "3", "4", "5"]),
                "shared_asset_refs": ["q01_stem_01"],
                "assets": [{"id": "q01_stem_01", "path": "figure.svg"}],
            },
        )
        self._write(
            self.generated_dir / EXAM_ID / "manifest.json",
            {
                "exam_id": EXAM_ID,
                "questions": [
                    {"id": "q01", "status": "generated"},
                    {"id": "q02", "status": "skipped-duplicate", "duplicate_of": "q01"},
                ],
            },
        )

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _write_valid_explanations(self, q01: dict | None = None) -> None:
        self._write(
            self.release_dir / "exams" / EXAM_ID / "explanations.json",
            {
                "schema_version": 1,
                "prompt_version": "explain_steps_v1",
                "questions": {"q01": q01 or _entry("original", "B"), "q02": _entry("original", "D")},
            },
        )
        self._write(
            self.generated_dir / EXAM_ID / "q01" / "explanation.json",
            {"schema_version": 1, "prompt_version": "explain_steps_v1", **_entry("variant", "C")},
        )
        stamp_content_hashes(self.release_dir, self.generated_dir, EXAM_ID)

    def _validate(self) -> dict:
        return validate_exam(self.release_dir, self.generated_dir, EXAM_ID)

    def test_valid_explanations_pass_and_skip_duplicate_variants(self) -> None:
        self._write_valid_explanations()
        report = self._validate()
        self.assertEqual(report["errors"], {})
        self.assertEqual(report["checked"], 3)

    def test_missing_explanations_are_errors(self) -> None:
        report = self._validate()
        self.assertIn(f"{EXAM_ID}/original", report["errors"])
        self.assertIn(f"{EXAM_ID}/variant/q01", report["errors"])

    def test_changed_question_text_or_figure_makes_explanation_stale(self) -> None:
        self._write_valid_explanations()
        (self.release_dir / "exams" / EXAM_ID / "assets" / "q01_stem_01.png").write_bytes(b"new-bytes")
        variant_path = self.generated_dir / EXAM_ID / "q01" / "question.json"
        variant = json.loads(variant_path.read_text(encoding="utf-8"))
        variant["stem_text"] = "How many suns?"
        self._write(variant_path, variant)

        errors = self._validate()["errors"]
        self.assertIn("stale", " ".join(errors[f"{EXAM_ID}/original/q01"]))
        self.assertIn("stale", " ".join(errors[f"{EXAM_ID}/variant/q01"]))
        self.assertNotIn(f"{EXAM_ID}/original/q02", errors)

    def test_stamp_never_overwrites_existing_hash(self) -> None:
        self._write_valid_explanations()
        (self.release_dir / "exams" / EXAM_ID / "assets" / "q01_stem_01.png").write_bytes(b"new-bytes")
        self.assertEqual(stamp_content_hashes(self.release_dir, self.generated_dir, EXAM_ID), [])

    def test_answer_and_answer_sentence_must_match_key(self) -> None:
        self._write_valid_explanations(_entry("original", "A", answer_sentence="So the answer is A."))
        errors = " ".join(self._validate()["errors"][f"{EXAM_ID}/original/q01"])
        self.assertIn("answer 'A' does not match", errors)
        self.assertIn("answer_sentence", errors)

    def test_independent_mismatch_must_be_flagged_with_a_note(self) -> None:
        self._write_valid_explanations(_entry("original", "B", independent_answer="C"))
        self.assertIn("disagrees", " ".join(self._validate()["errors"][f"{EXAM_ID}/original/q01"]))

        self._write_valid_explanations(
            _entry("original", "B", independent_answer="C", review={"status": "flagged", "note": None})
        )
        self.assertIn("review.note", " ".join(self._validate()["errors"][f"{EXAM_ID}/original/q01"]))

        self._write_valid_explanations(
            _entry("original", "B", independent_answer="C", review={"status": "flagged", "note": "Counted 5 stars."})
        )
        report = self._validate()
        self.assertEqual(report["errors"], {})
        self.assertEqual(report["flagged"], [f"{EXAM_ID}/original/q01: Counted 5 stars."])

    def test_unsolved_independent_answer_must_be_flagged(self) -> None:
        self._write_valid_explanations(_entry("original", "B", independent_answer=None))
        self.assertIn("disagrees", " ".join(self._validate()["errors"][f"{EXAM_ID}/original/q01"]))

        self._write_valid_explanations(
            _entry("original", "B", independent_answer=None, review={"status": "flagged", "note": "Could not count."})
        )
        self.assertEqual(self._validate()["errors"], {})

    def test_choice_feedback_covers_exactly_the_wrong_choices(self) -> None:
        self._write_valid_explanations(_entry("original", "B", choice_feedback={"A": "Too few.", "B": "Right."}))
        self.assertIn("choice_feedback", " ".join(self._validate()["errors"][f"{EXAM_ID}/original/q01"]))

    def test_contradictory_answer_claim_is_rejected_but_lowercase_article_is_not(self) -> None:
        self._write_valid_explanations(
            _entry("original", "B", steps=["Count the stars.", "The answer is a number. Option C is correct."])
        )
        errors = " ".join(self._validate()["errors"][f"{EXAM_ID}/original/q01"])
        self.assertIn("wrong answer: ['C']", errors)

        self._write_valid_explanations(
            _entry("original", "B", steps=["Count the stars.", "The answer is a four. Point E is right of the tree."])
        )
        self.assertEqual(self._validate()["errors"], {})

    def test_content_hash_ignores_unreferenced_fields(self) -> None:
        ref = load_original_questions(self.release_dir, EXAM_ID)[1]
        before = question_content_hash(ref)
        ref.question["points"] = 5
        self.assertEqual(question_content_hash(ref), before)
        self.assertEqual(len(load_variant_questions(self.generated_dir, EXAM_ID)), 1)


if __name__ == "__main__":
    unittest.main()
