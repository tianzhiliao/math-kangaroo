from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from ..config import get_settings
from ..openai_client import get_openai_client
from ..question_loader import QuestionSnapshot, load_question_snapshot, validate_selected_label
from .cache import ExplanationCache

PROMPT_VERSION = "grade1_v3"
MAX_EXPLANATION_ATTEMPTS = 2

ANSWER_CLAIM_PATTERNS = (
    re.compile(r"\banswer\s+is\s+([A-E])\b", re.IGNORECASE),
    re.compile(r"\bcorrect\s+answer\s+is\s+([A-E])\b", re.IGNORECASE),
    re.compile(r"\boption\s+([A-E])\s+is\s+correct\b", re.IGNORECASE),
    re.compile(r"\b([A-E])\s+is\s+correct\b", re.IGNORECASE),
)

EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string"},
        "final_answer": {"type": "string"},
    },
    "required": ["explanation", "final_answer"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """
You are a friendly elementary math tutor writing answer explanations for children aged 6-7 (Grade 1-2).

Rules:
- Write in English only.
- Use very simple words and short sentences.
- Sound warm, clear, and encouraging.
- Explain the idea step by step in a way a young child can understand.
- If the problem is about counting, comparing, shapes, or pictures, describe the steps clearly.
- Do not use difficult math words unless they are absolutely necessary.
- Do not mention anything that is not provided in the input.
- Keep the explanation short: 3 to 5 sentences.
- Always say why the correct answer is correct.
- End with a simple answer sentence like: "So the answer is B."
""".strip()


def generate_explanation(
    *,
    exam_id: str,
    question_number: int,
    selected_label: str | None,
    force_refresh: bool = False,
    cache: ExplanationCache | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    cache = cache or ExplanationCache()
    snapshot = load_question_snapshot(exam_id, question_number)
    selected_label = validate_selected_label(snapshot, selected_label)
    cache_key_payload = {
        "exam_id": exam_id,
        "question_number": question_number,
        "selected_label": selected_label,
        "model": settings.openai_explanation_model,
        "prompt_version": PROMPT_VERSION,
    }
    cache_key = cache.build_key(cache_key_payload)
    cached = cache.load(cache_key) if not force_refresh else None
    if cached is not None:
        return {
            **cached,
            "cache_hit": True,
        }

    try:
        client = get_openai_client()
    except RuntimeError as exc:  # pragma: no cover - runtime-only paths
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    explanation: str | None = None
    for _ in range(MAX_EXPLANATION_ATTEMPTS):
        response = client.responses.create(
            model=settings.openai_explanation_model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": _build_user_content(snapshot, selected_label),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "question_explanation",
                    "strict": True,
                    "schema": EXPLANATION_SCHEMA,
                }
            },
        )
        try:
            parsed = json.loads(response.output_text)
        except json.JSONDecodeError:
            continue

        raw_explanation = str(parsed.get("explanation", "")).strip()
        if not raw_explanation:
            continue
        final_answer = _normalize_label(str(parsed.get("final_answer", "")))
        if final_answer != snapshot.correct_label:
            continue
        if _has_contradictory_answer_claim(raw_explanation, snapshot.correct_label):
            continue
        explanation = _finalize_explanation(raw_explanation, snapshot.correct_label)
        break

    if explanation is None:
        explanation = _finalize_explanation(
            _fallback_explanation(snapshot.correct_label, selected_label),
            snapshot.correct_label,
        )
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = {
        "exam_id": exam_id,
        "question_number": question_number,
        "selected_label": selected_label,
        "correct_label": snapshot.correct_label,
        "explanation": explanation,
        "model": settings.openai_explanation_model,
        "generated_at": generated_at,
    }
    cache.store(cache_key, payload)
    return {
        **payload,
        "cache_hit": False,
    }


def _build_user_content(snapshot: QuestionSnapshot, selected_label: str | None) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": _build_question_text(snapshot, selected_label),
        }
    ]
    for asset in snapshot.stem_assets:
        content.append({"type": "input_text", "text": asset.label})
        content.append({"type": "input_image", "image_url": asset.data_url})
    for choice in snapshot.choices:
        assets = snapshot.choice_assets.get(choice["label"], [])
        for asset in assets:
            content.append({"type": "input_text", "text": asset.label})
            content.append({"type": "input_image", "image_url": asset.data_url})
    return content


def _build_question_text(snapshot: QuestionSnapshot, selected_label: str | None) -> str:
    choice_lines = []
    for choice in snapshot.choices:
        has_image = bool(snapshot.choice_assets.get(choice["label"]))
        image_note = " Has an image." if has_image else ""
        choice_text = choice["text"].strip() or "No text."
        choice_lines.append(f"- {choice['label']}: {choice_text}{image_note}")

    if snapshot.stem_assets:
        stem_visual_note = f"The question has {len(snapshot.stem_assets)} stem image(s)."
    else:
        stem_visual_note = "The question has no stem image."

    if selected_label:
        selection_note = f"The student chose {selected_label}."
    else:
        selection_note = "No student choice was provided."

    return "\n".join(
        [
            "Generate a child-friendly explanation for this multiple-choice math question.",
            "",
            "Student age: 6-7",
            "Grade: 1-2",
            "Language: English",
            "",
            f"Exam ID: {snapshot.exam_id}",
            f"Question number: {snapshot.question_number}",
            f"Year: {snapshot.year}",
            f"Level: {snapshot.level}",
            f"Question stem: {snapshot.stem_text or 'No stem text.'}",
            stem_visual_note,
            "",
            "Choices:",
            *choice_lines,
            "",
            selection_note,
            f"Correct answer: {snapshot.correct_label}",
            "",
            "Requirements:",
            "- Make it easy for a 6-7-year-old child to understand.",
            "- Use short sentences.",
            "- Explain why the correct answer is right.",
            "- If the student chose the wrong answer, gently point them back to the correct one.",
            '- End with the exact style: "So the answer is X."',
        ]
    )


def _finalize_explanation(explanation: str, correct_label: str) -> str:
    if not explanation:
        return f"So the answer is {correct_label}."
    final_sentence = f"So the answer is {correct_label}."
    normalized = explanation.rstrip()
    if normalized.endswith(final_sentence):
        return normalized
    if normalized[-1] not in ".!?":
        normalized = f"{normalized}."
    return f"{normalized} {final_sentence}"


def _normalize_label(value: str) -> str:
    match = re.search(r"[A-E]", value.upper())
    if not match:
        return ""
    return match.group(0)


def _has_contradictory_answer_claim(explanation: str, correct_label: str) -> bool:
    claims: set[str] = set()
    for pattern in ANSWER_CLAIM_PATTERNS:
        claims.update(match.group(1).upper() for match in pattern.finditer(explanation))
    return any(label != correct_label for label in claims)


def _fallback_explanation(correct_label: str, selected_label: str | None) -> str:
    if selected_label and selected_label != correct_label:
        return (
            f"Let's check each clue carefully and compare all options. "
            f"Option {correct_label} matches the clues best. "
            f"You chose {selected_label}, but that option misses part of the clue."
        )
    return (
        "Let's check the clues one by one and match them with the options. "
        f"Option {correct_label} fits the clues best. "
        "Great job thinking it through."
    )
