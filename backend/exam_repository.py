from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import threading


EXAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ExamRepositoryError(Exception):
    """Base error for exam data lookups."""


class ExamNotFoundError(ExamRepositoryError):
    """Raised when the requested exam JSON file does not exist."""


class QuestionNotFoundError(ExamRepositoryError):
    """Raised when the requested question does not exist."""


class EmptyStemTextError(ExamRepositoryError):
    """Raised when a question exists but has no readable stem text."""


@dataclass(frozen=True)
class ExamStem:
    exam_id: str
    question_id: int
    stem_text: str


class ExamRepository:
    def __init__(self, exam_data_dir: Path) -> None:
        self._exam_data_dir = exam_data_dir
        self._cache: dict[str, dict] = {}
        self._lock = threading.Lock()

    def list_stems(self) -> list[ExamStem]:
        stems: list[ExamStem] = []
        for exam_path in sorted(self._exam_data_dir.glob("Exam_*.json")):
            exam_id = exam_path.stem
            exam = self._load_exam(exam_id)
            for question in exam.get("questions", []):
                stem_text = str(question.get("stem_text", "")).strip()
                if not stem_text:
                    continue
                stems.append(
                    ExamStem(
                        exam_id=exam_id,
                        question_id=int(question["id"]),
                        stem_text=stem_text,
                    )
                )
        return stems

    def get_stem(self, exam_id: str, question_id: int) -> ExamStem:
        exam = self._load_exam(exam_id)
        for question in exam.get("questions", []):
            if int(question.get("id", -1)) != question_id:
                continue

            stem_text = str(question.get("stem_text", "")).strip()
            if not stem_text:
                raise EmptyStemTextError(
                    f"Question {question_id} in {exam_id} does not have stem text."
                )

            return ExamStem(exam_id=exam_id, question_id=question_id, stem_text=stem_text)

        raise QuestionNotFoundError(f"Question {question_id} was not found in {exam_id}.")

    def _load_exam(self, exam_id: str) -> dict:
        if not EXAM_ID_PATTERN.fullmatch(exam_id):
            raise ExamNotFoundError(f"Invalid exam id: {exam_id}")

        with self._lock:
            cached = self._cache.get(exam_id)
            if cached is not None:
                return cached

        exam_path = (self._exam_data_dir / f"{exam_id}.json").resolve()
        if not exam_path.is_file() or not exam_path.is_relative_to(self._exam_data_dir.resolve()):
            raise ExamNotFoundError(f"Exam {exam_id} was not found.")

        exam = json.loads(exam_path.read_text(encoding="utf-8"))
        with self._lock:
            self._cache[exam_id] = exam
        return exam

