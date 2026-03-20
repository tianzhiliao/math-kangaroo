from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

VERIFIED_ANSWER_KEYS_PATH = Path(__file__).with_name("verified_answer_keys.json")
_REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def load_verified_answer_keys() -> dict[str, dict[str, str]]:
    payload = json.loads(VERIFIED_ANSWER_KEYS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("verified_answer_keys.json must contain an object at the top level.")

    normalized: dict[str, dict[str, str]] = {}
    for exam_id, answers in payload.items():
        if not isinstance(exam_id, str) or not isinstance(answers, dict):
            raise ValueError("verified_answer_keys.json entries must map exam_id strings to answer objects.")
        normalized[exam_id] = {str(question): str(answer) for question, answer in answers.items()}
    return normalized


def verified_answer_key_for_exam(exam_id: str) -> dict[str, str] | None:
    answer_keys = load_verified_answer_keys()
    answers = answer_keys.get(exam_id)
    return dict(answers) if answers else None


def verified_answer_key_ref(exam_id: str) -> str:
    relative_path = VERIFIED_ANSWER_KEYS_PATH.relative_to(_REPO_ROOT).as_posix()
    return f"{relative_path}#{exam_id}"
