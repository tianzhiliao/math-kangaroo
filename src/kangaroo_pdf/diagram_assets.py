from __future__ import annotations

from typing import Any

import fitz

from .visual_assets import (
    build_page_visual_cache as _build_page_visual_cache,
    choice_has_semantic_text,
    extract_question_visual_assets,
    round_rect,
)


def build_page_word_cache(doc: fitz.Document) -> dict[int, list[dict[str, Any]]]:
    cache: dict[int, list[dict[str, Any]]] = {}
    for page_index, page in enumerate(doc):
        cache[page_index] = [
            {
                "text": text,
                "rect": fitz.Rect(x0, y0, x1, y1),
            }
            for x0, y0, x1, y1, text, *_ in page.get_text("words")
        ]
    return cache


def build_page_visual_cache(doc: fitz.Document) -> dict[int, dict[str, list[fitz.Rect]]]:
    return _build_page_visual_cache(doc)


def choice_requires_asset(text: str) -> bool:
    return not choice_has_semantic_text(text)


def _visual_counts_from_audit(audit: dict[str, Any]) -> dict[str, int]:
    image_count = 0
    drawing_count = 0
    for candidate in audit.get("visual_candidates", []):
        sources = set(candidate.get("sources", []))
        if "image" in sources:
            image_count += 1
        if "drawing" in sources or "render" in sources:
            drawing_count += 1
    return {"images": image_count, "drawings": drawing_count}


def extract_question_assets(
    document_family: str,
    page: fitz.Page,
    question_number: int,
    question_bbox: fitz.Rect,
    previous_anchor: Any | None,
    page_words: list[dict[str, Any]],
    page_visuals: dict[str, list[fitz.Rect]],
    choices: list[dict[str, Any]],
    assets_dir: Any,
    year: int | None = None,
) -> dict[str, Any]:
    del previous_anchor
    del page_words
    payload = extract_question_visual_assets(
        family=document_family,
        year=year,
        page=page,
        question_number=question_number,
        question_bbox=question_bbox,
        choices=choices,
        visual_cache=page_visuals,
        assets_dir=assets_dir,
    )
    reference_bbox = fitz.Rect(question_bbox)
    for asset in payload["assets"]:
        reference_bbox |= fitz.Rect(asset["bbox"])
    reference_bbox |= question_bbox
    return {
        "assets": payload["assets"],
        "shared_asset_refs": payload["shared_asset_refs"],
        "option_asset_refs": payload["option_asset_refs"],
        "reference_bbox": round_rect(reference_bbox),
        "visual_counts": _visual_counts_from_audit(payload["audit"]),
        "assignment_audit": payload["audit"],
    }
