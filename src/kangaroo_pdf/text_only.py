from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

try:
    import pdfplumber
except ModuleNotFoundError:  # pragma: no cover - optional dependency in local envs
    pdfplumber = None

from .pipeline import (
    OPTION_LABELS,
    build_exam_id,
    classify_document,
    collapse_inline,
    collect_question_anchors,
    filter_noise_lines,
    parse_choices,
    question_bbox_for_anchor,
    question_page_window,
    round_rect,
)

SECTION_BREAK_RE = re.compile(
    r"^(?:PART\s+[ABC]\b.*|[\-\u2013\u2014 ]*\d+\s*Point Questions?[\-\u2013\u2014 ]*)$",
    re.IGNORECASE,
)
FOOTER_NOISE_RE = re.compile(
    r"(copyright|permission|all rights reserved|do not duplicate|math kangaroo|page \d+|point questions?)",
    re.IGNORECASE,
)
HEADER_NOISE_RE = re.compile(
    r"(grade\s*1-2|part\s+[abc]|point questions?|name:|school:|class:)",
    re.IGNORECASE,
)
OPTION_TOKEN_RE = re.compile(r"^(?:\(([A-E])\)|([A-E])[.)])$")
ALLOWED_TEXT_CHAR_RE = re.compile(
    r"[^A-Za-zÀ-ÖØ-öø-ÿ0-9\s\.,;:!\?\"'’‘“”()\[\]\{\}\-–—+*/=%<>$#@&^_|~×÷√°′″≤≥≠∞·]"
)
SUSPICIOUS_TOKEN_RE = re.compile(r"(?:\d+[ilf]\b|\b[A-E]l\b|\([A-E]\)[a-z]\b)")
VISUAL_SEQUENCE_RE = re.compile(r"(?:\b[0-9A-Za-z+\-]\b(?:\s+|$)){4,}")
VISUAL_LABEL_RE = re.compile(r"\b(?:START|END)\b(?:\s+\b(?:START|END)\b)*", re.IGNORECASE)
VISUAL_HINT_RE = re.compile(
    r"\b(shown below|shown on|figure|diagram|picture|piece|missing|card|shape|grid)\b",
    re.IGNORECASE,
)
NUMBER_WORDS = {
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
}


def _strip_question_number(text: str, question_number: int) -> str:
    return re.sub(rf"^\s*{question_number}\.\s*", "", text, count=1)


def _clean_question_text(raw_text: str) -> str:
    cleaned_lines: list[str] = []
    for line in raw_text.splitlines():
        compact = collapse_inline(line)
        if not compact:
            continue
        if SECTION_BREAK_RE.match(compact):
            break
        if FOOTER_NOISE_RE.search(compact) or HEADER_NOISE_RE.search(compact):
            continue
        cleaned_lines.append(compact)
    return "\n".join(cleaned_lines).strip()


def _group_rows(
    words: list[tuple[float, float, float, float, str, int, int, int]],
    tolerance: float = 3.2,
) -> list[list[tuple[float, float, float, float, str, int, int, int]]]:
    rows: list[list[tuple[float, float, float, float, str, int, int, int]]] = []
    for word in sorted(words, key=lambda item: (item[1], item[0])):
        if rows and abs(rows[-1][0][1] - word[1]) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda item: item[0])
    return rows


def _option_label_from_token(token: str) -> str | None:
    compact = collapse_inline(token)
    match = OPTION_TOKEN_RE.fullmatch(compact)
    if match:
        return match.group(1) or match.group(2)
    return None


def _visual_masks(page: fitz.Page) -> list[fitz.Rect]:
    masks: list[fitz.Rect] = []
    padding = 1.0
    page_w = float(page.rect.width)
    page_h = float(page.rect.height)
    for image in page.get_images(full=True):
        xref = image[0]
        for rect in page.get_image_rects(xref):
            if rect.width * rect.height >= 180:
                masks.append(
                    fitz.Rect(
                        rect.x0 - padding,
                        rect.y0 - padding,
                        rect.x1 + padding,
                        rect.y1 + padding,
                    )
                )
    for drawing in page.get_drawings():
        rect = drawing.get("rect") if isinstance(drawing, dict) else None
        if rect is None:
            continue
        if rect.width <= 0.01 or rect.height <= 0.01:
            continue
        area = rect.width * rect.height
        aspect = rect.width / rect.height
        if area < 260:
            continue
        # Ignore long guide lines and near-full-page frames that erase valid text.
        if aspect > 8.0 or aspect < 0.125:
            continue
        if rect.width >= page_w * 0.92 and rect.height <= page_h * 0.08:
            continue
        if rect.height >= page_h * 0.92 and rect.width <= page_w * 0.08:
            continue
        if area >= 260:
            masks.append(
                fitz.Rect(
                    rect.x0 - padding,
                    rect.y0 - padding,
                    rect.x1 + padding,
                    rect.y1 + padding,
                )
            )
    return masks


def _collect_filtered_words(
    page: fitz.Page,
    bbox: fitz.Rect,
) -> tuple[list[tuple[float, float, float, float, str, int, int, int]], dict[str, int]]:
    masks = _visual_masks(page)
    page_h = float(page.rect.height)
    header_cutoff = page_h * 0.12
    footer_cutoff = page_h * 0.90

    kept: list[tuple[float, float, float, float, str, int, int, int]] = []
    stats = {
        "dropped_header_footer": 0,
        "dropped_visual_overlap": 0,
        "dropped_noise_token": 0,
        "dropped_by_bbox_margin": 0,
    }
    edge_margin = 0.8
    for word in page.get_text("words", clip=bbox):
        x0, y0, x1, y1, text, block, line, wno = word
        token = collapse_inline(text)
        if not token:
            continue
        rect = fitz.Rect(x0, y0, x1, y1)
        if y0 <= bbox.y0 + edge_margin or y1 >= bbox.y1 - edge_margin:
            stats["dropped_by_bbox_margin"] += 1
            continue
        if y0 <= header_cutoff or y1 >= footer_cutoff:
            stats["dropped_header_footer"] += 1
            continue
        if any(mask.intersects(rect) for mask in masks):
            stats["dropped_visual_overlap"] += 1
            continue
        if FOOTER_NOISE_RE.search(token):
            stats["dropped_noise_token"] += 1
            continue
        kept.append((x0, y0, x1, y1, token, block, line, wno))
    return kept, stats


def _split_stem_and_choices(
    words: list[tuple[float, float, float, float, str, int, int, int]],
    question_number: int,
) -> tuple[str, dict[str, str], bool]:
    rows = _group_rows(words)
    stem_parts: list[str] = []
    choice_tokens: dict[str, list[str]] = {label: [] for label in OPTION_LABELS}
    in_choices = False
    last_label: str | None = None
    saw_any_option_label = False

    for row in rows:
        row_labels: list[tuple[str, float, float]] = []
        for x0, _y0, x1, _y1, token, *_ in row:
            label = _option_label_from_token(token)
            if label:
                row_labels.append((label, x0, x1))
        if row_labels:
            in_choices = True
            saw_any_option_label = True
            row_labels.sort(key=lambda item: item[1])
            for idx, (label, _start_x, end_x) in enumerate(row_labels):
                next_start = row_labels[idx + 1][1] if idx + 1 < len(row_labels) else float("inf")
                seg_tokens: list[str] = []
                for x0, _y0, x1, _y1, token, *_ in row:
                    if _option_label_from_token(token):
                        continue
                    if x0 >= end_x - 1.0 and x1 <= next_start + 1.0:
                        seg_tokens.append(token)
                choice_tokens[label].extend(seg_tokens)
                last_label = label
            continue

        row_text = collapse_inline(" ".join(token for *_rest, token, _b, _l, _w in row))
        if not row_text:
            continue
        if SECTION_BREAK_RE.match(row_text):
            break
        if in_choices and last_label:
            # Continuation line for the last seen option label.
            choice_tokens[last_label].extend(row_text.split())
        else:
            stem_parts.append(row_text)

    stem_text = _strip_question_number(collapse_inline(" ".join(stem_parts)), question_number)
    choices = {label: collapse_inline(" ".join(choice_tokens[label])) for label in OPTION_LABELS}
    non_empty_choice_count = sum(1 for label in OPTION_LABELS if choices[label])
    longest_choice_len = max((len(choices[label]) for label in OPTION_LABELS), default=0)
    shortest_non_empty = min((len(choices[label]) for label in OPTION_LABELS if choices[label]), default=0)
    low_confidence = (
        (not saw_any_option_label)
        or (non_empty_choice_count == 0 and bool(stem_text))
        or (non_empty_choice_count <= 1 and longest_choice_len >= 35)
        or (non_empty_choice_count >= 2 and shortest_non_empty <= 2 and longest_choice_len >= 70)
    )
    return stem_text, choices, low_confidence


def _rows_to_text(rows: list[list[tuple[float, float, float, float, str, int, int, int]]]) -> str:
    lines: list[str] = []
    for row in rows:
        line = collapse_inline(" ".join(token for *_rest, token, _b, _l, _w in row))
        if line:
            lines.append(line)
    return "\n".join(lines)


def _remove_tail_noise(text: str) -> str:
    cleaned = collapse_inline(text)
    if not cleaned:
        return ""
    hit = FOOTER_NOISE_RE.search(cleaned)
    if hit:
        cleaned = cleaned[: hit.start()].strip()
    cleaned = re.sub(r"\bi\b$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _strip_visual_leakage_text(text: str) -> str:
    cleaned = collapse_inline(text)
    if not cleaned:
        return ""

    # Remove repeated map/diagram labels (e.g. START A B C D E).
    cleaned = VISUAL_LABEL_RE.sub("", cleaned).strip()
    cleaned = re.sub(
        r"\b(?:Green|Red|Blue|Yellow|Black|White)\b(?:\s+\b(?:Green|Red|Blue|Yellow|Black|White)\b){1,}",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"(?:\+\s*){2,}=\s*\d+\b", "", cleaned)

    # Remove long runs of isolated symbols/digits/letters that typically come from diagrams.
    cleaned = VISUAL_SEQUENCE_RE.sub(" ", cleaned)
    cleaned = re.sub(r"(?<=[\.\:])\s*(?:\d+\s+){1,4}(?=[A-Z])", " ", cleaned)
    cleaned = re.sub(r"(?<=[\.\:])\s+[A-Z]\s+(?=[A-Z][a-z])", " ", cleaned)

    tokens = cleaned.split()
    kept: list[str] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        compact = re.sub(r"[^A-Za-z0-9]", "", token)
        if compact.isdigit():
            run_start = idx
            run_end = idx
            numbers = [int(compact)]
            while run_end + 1 < len(tokens):
                next_compact = re.sub(r"[^A-Za-z0-9]", "", tokens[run_end + 1])
                if next_compact.isdigit():
                    numbers.append(int(next_compact))
                    run_end += 1
                else:
                    break
            is_consecutive = len(numbers) >= 4 and all((numbers[i + 1] - numbers[i]) in (0, 1) for i in range(len(numbers) - 1))
            is_visual_numeric_run = len(numbers) >= 4 and all(len(re.sub(r"[^0-9]", "", token)) <= 2 for token in tokens[run_start : run_end + 1])
            if is_visual_numeric_run:
                idx = run_end + 1
                continue
            if is_consecutive:
                idx = run_end + 1
                continue
            kept.extend(tokens[run_start : run_end + 1])
            idx = run_end + 1
            continue
        kept.append(token)
        idx += 1

    cleaned = collapse_inline(" ".join(kept))
    cleaned = re.sub(r"(?:\s*[+\-*/=]\s*)+$", "", cleaned).strip()
    return cleaned


def _strip_choice_fragment_noise(text: str) -> str:
    cleaned = collapse_inline(text)
    if not cleaned:
        return ""
    if re.fullmatch(r"[a-z]", cleaned):
        return ""
    # OCR near diagram labels can leave a dangling single digit, e.g. "five 1".
    match = re.fullmatch(r"([A-Za-z]{3,})\s+(\d)", cleaned)
    if match and match.group(1).lower() in NUMBER_WORDS:
        return match.group(1)
    return cleaned


def _clear_visual_option_token(
    *,
    stem_text: str,
    choice_text: str,
) -> str:
    cleaned = collapse_inline(choice_text)
    if not cleaned:
        return ""
    lowered_stem = collapse_inline(stem_text).lower()
    is_numeric_pair = bool(re.fullmatch(r"(?:\d+\s+){1,}\d+", cleaned))
    is_symbol_sequence = bool(re.fullmatch(r"(?:[A-Z]\s+){2,}[A-Z]", cleaned))
    visual_stem_hint = any(
        hint in lowered_stem
        for hint in (
            "which figure",
            "view from the front",
            "what does the sheet look",
            "which piece is not used",
            "which boat is mine",
            "in what order will she find",
        )
    )
    if visual_stem_hint and (is_numeric_pair or is_symbol_sequence):
        return ""
    return cleaned


def _has_visual_leakage_pattern(text: str) -> bool:
    candidate = collapse_inline(text)
    if not candidate:
        return False
    if VISUAL_SEQUENCE_RE.search(candidate):
        return True
    number_tokens = [int(tok) for tok in re.findall(r"\b\d+\b", candidate)]
    if (
        len(number_tokens) >= 6
        and max(number_tokens) - min(number_tokens) >= 5
        and all((number_tokens[i + 1] - number_tokens[i]) in (0, 1) for i in range(len(number_tokens) - 1))
    ):
        return True
    if re.search(r"\bSTART\b.*\b[A-E]\b(?:\s+\b[A-E]\b){2,}", candidate):
        return True
    return False


def _has_live_suspicious_token(text: str) -> bool:
    return bool(SUSPICIOUS_TOKEN_RE.search(collapse_inline(text)))


def _normalize_option_payload(choice_texts: dict[str, str]) -> dict[str, str]:
    return {label: collapse_inline(choice_texts.get(label, "")) for label in OPTION_LABELS}


def _normalize_text_quality(text: str, *, context: str) -> tuple[str, dict[str, Any]]:
    edits: list[dict[str, str]] = []
    original = text
    normalized = unicodedata.normalize("NFKC", text)
    if normalized != text:
        edits.append({"type": "unicode_nfkc", "before": text, "after": normalized})
    compact = collapse_inline(normalized)
    if compact != normalized:
        edits.append({"type": "collapse_inline_whitespace", "before": normalized, "after": compact})
    normalized = compact

    control_stripped = "".join(ch for ch in normalized if unicodedata.category(ch)[0] != "C")
    if control_stripped != normalized:
        edits.append({"type": "strip_control_chars", "before": normalized, "after": control_stripped})
    normalized = control_stripped

    dangling_suffix = re.sub(r"(?<=\d)[ilf]\b", "", normalized)
    if dangling_suffix != normalized:
        edits.append({"type": "strip_numeric_dangling_suffix", "before": normalized, "after": dangling_suffix})
    normalized = dangling_suffix

    if context == "choice":
        fixed_choice_token = re.sub(r"\b([A-E])l\b", r"\1", normalized)
        if fixed_choice_token != normalized:
            edits.append({"type": "repair_choice_ocr_confusion", "before": normalized, "after": fixed_choice_token})
        normalized = fixed_choice_token
        stripped_number_tail = re.sub(
            r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\s+\d\b",
            r"\1",
            normalized,
            flags=re.IGNORECASE,
        )
        if stripped_number_tail != normalized:
            edits.append(
                {
                    "type": "strip_number_word_dangling_digit",
                    "before": normalized,
                    "after": stripped_number_tail,
                }
            )
        normalized = stripped_number_tail

    illegal_chars = ALLOWED_TEXT_CHAR_RE.findall(normalized)
    if illegal_chars:
        cleaned = ALLOWED_TEXT_CHAR_RE.sub("", normalized)
        edits.append({"type": "strip_disallowed_chars", "before": normalized, "after": cleaned})
        normalized = cleaned

    suspicious_tokens = sorted(set(SUSPICIOUS_TOKEN_RE.findall(original + " " + normalized)))
    final_text = collapse_inline(normalized)
    return final_text, {
        "original_text": original,
        "normalized_text": final_text,
        "normalization_edits": edits,
        "illegal_chars_removed": illegal_chars,
        "illegal_char_count": len(illegal_chars),
        "suspicious_tokens": suspicious_tokens,
    }


def _choice_alignment_conflict(choices_a: dict[str, str], choices_b: dict[str, str]) -> bool:
    norm_a = _normalize_option_payload(choices_a)
    norm_b = _normalize_option_payload(choices_b)
    non_empty_a = sum(1 for label in OPTION_LABELS if norm_a[label])
    non_empty_b = sum(1 for label in OPTION_LABELS if norm_b[label])
    if abs(non_empty_a - non_empty_b) >= 3:
        return True
    mismatch_count = 0
    for label in OPTION_LABELS:
        ta = norm_a[label]
        tb = norm_b[label]
        if not ta or not tb:
            continue
        # Ignore whitespace/punctuation-only drift across fallback channels.
        ca = re.sub(r"[^A-Za-z0-9]+", "", ta).lower()
        cb = re.sub(r"[^A-Za-z0-9]+", "", tb).lower()
        if ca and cb and ca != cb:
            mismatch_count += 1
    return mismatch_count >= 2


def _fallback_with_pdfplumber(plumber_page: Any, bbox: fitz.Rect, question_number: int) -> tuple[str, dict[str, str]]:
    page_x0, page_y0, page_x1, page_y1 = plumber_page.bbox
    crop_bbox = (
        max(page_x0, min(float(bbox.x0), page_x1)),
        max(page_y0, min(float(bbox.y0), page_y1)),
        max(page_x0, min(float(bbox.x1), page_x1)),
        max(page_y0, min(float(bbox.y1), page_y1)),
    )
    crop = plumber_page.crop(crop_bbox, strict=False)
    raw_text = crop.extract_text(x_tolerance=1.2, y_tolerance=2.8) or ""
    cleaned = _clean_question_text(filter_noise_lines(raw_text))
    cleaned = _strip_question_number(cleaned, question_number)
    stem_text, parsed_choices = parse_choices(cleaned)
    choice_texts = {choice["label"]: _remove_tail_noise(choice["text"]) for choice in parsed_choices}
    return _remove_tail_noise(stem_text), choice_texts


def _fallback_with_filtered_words(
    words: list[tuple[float, float, float, float, str, int, int, int]],
    question_number: int,
) -> tuple[str, dict[str, str]]:
    raw_text = _rows_to_text(_group_rows(words))
    cleaned = _clean_question_text(filter_noise_lines(raw_text))
    cleaned = _strip_question_number(cleaned, question_number)
    stem_text, parsed_choices = parse_choices(cleaned)
    choice_texts = {choice["label"]: _remove_tail_noise(choice["text"]) for choice in parsed_choices}
    return _remove_tail_noise(stem_text), choice_texts


def _fallback_with_text_block_raw(page: fitz.Page, bbox: fitz.Rect, question_number: int) -> tuple[str, dict[str, str]]:
    raw_text = page.get_text("text", clip=bbox)
    cleaned = _clean_question_text(filter_noise_lines(raw_text))
    cleaned = _strip_question_number(cleaned, question_number)
    stem_text, parsed_choices = parse_choices(cleaned)
    choice_texts = {choice["label"]: _remove_tail_noise(choice["text"]) for choice in parsed_choices}
    return _remove_tail_noise(stem_text), choice_texts


def _score_candidate(stem_text: str, choice_texts: dict[str, str]) -> int:
    # Favor candidates with richer text, but punish noisy tails.
    stem_tokens = re.findall(r"[A-Za-z]{3,}", _remove_tail_noise(stem_text))
    non_empty_choices = sum(1 for label in OPTION_LABELS if collapse_inline(choice_texts.get(label, "")))
    choice_tokens = sum(len(re.findall(r"[A-Za-z0-9]+", choice_texts.get(label, ""))) for label in OPTION_LABELS)
    noise_penalty = 40 if FOOTER_NOISE_RE.search(" ".join(choice_texts.values())) else 0
    return (len(stem_tokens) * 6) + (non_empty_choices * 10) + choice_tokens - noise_penalty


def _semantic_readability_score(stem_text: str, choice_texts: dict[str, str]) -> float:
    stem_words = re.findall(r"[A-Za-z]{3,}", stem_text)
    non_empty = sum(1 for label in OPTION_LABELS if collapse_inline(choice_texts.get(label, "")))
    noise = 1 if FOOTER_NOISE_RE.search(stem_text + " " + " ".join(choice_texts.values())) else 0
    raw = (len(stem_words) * 0.08) + (non_empty * 0.15) - (noise * 0.4)
    return round(max(0.0, min(1.0, raw)), 3)


def evaluate_text_only_blocking_errors(
    payload: dict[str, Any],
    *,
    max_high_risk: int = 0,
    max_option_alignment_conflict: int = 0,
    max_illegal_char_ratio: float = 0.0,
) -> list[str]:
    summary = payload.get("quality_summary", {})
    errors: list[str] = []
    high_risk_count = int(summary.get("high_risk_question_count", 0))
    if high_risk_count > max_high_risk:
        errors.append(
            f"high_risk_question_count={high_risk_count} exceeds max_high_risk={max_high_risk}"
        )
    conflict_count = int(summary.get("option_alignment_conflict_count", 0))
    if conflict_count > max_option_alignment_conflict:
        errors.append(
            "option_alignment_conflict_count="
            f"{conflict_count} exceeds max_option_alignment_conflict={max_option_alignment_conflict}"
        )
    max_observed_ratio = float(summary.get("max_illegal_char_ratio", 0.0))
    if max_observed_ratio > max_illegal_char_ratio:
        errors.append(
            f"max_illegal_char_ratio={max_observed_ratio:.4f} exceeds "
            f"max_illegal_char_ratio={max_illegal_char_ratio:.4f}"
        )
    return errors


def extract_text_only_exam(pdf_path: Path | str) -> dict[str, Any]:
    source_pdf = Path(pdf_path).resolve()
    document = classify_document(source_pdf)
    if not document.question_count:
        raise ValueError(f"Cannot determine question_count for {source_pdf.name}")

    doc = fitz.open(source_pdf.as_posix())
    plumber_doc = pdfplumber.open(source_pdf.as_posix()) if pdfplumber is not None else None
    try:
        start_page_index, end_page_index = question_page_window(document, doc)
        anchors = collect_question_anchors(doc, document.question_count, start_page_index, end_page_index)
        questions: list[dict[str, Any]] = []
        summary = {
            "footer_noise_detected_count": 0,
            "image_text_leak_suspected_count": 0,
            "option_alignment_low_confidence_count": 0,
            "option_alignment_conflict_count": 0,
            "suspicious_text_question_count": 0,
            "normalization_edit_count": 0,
            "total_illegal_char_count": 0,
            "max_illegal_char_ratio": 0.0,
            "high_risk_question_count": 0,
        }

        for index, anchor in enumerate(anchors):
            next_anchor = anchors[index + 1] if index + 1 < len(anchors) else None
            page = doc[anchor.page_index]
            bbox = fitz.Rect(question_bbox_for_anchor(doc, anchor, next_anchor))

            words, drop_stats = _collect_filtered_words(page, bbox)
            stem_a, choices_a, option_alignment_low_confidence = _split_stem_and_choices(words, anchor.number)
            stem_a = _remove_tail_noise(stem_a)
            choices_a = {label: _remove_tail_noise(choices_a.get(label, "")) for label in OPTION_LABELS}
            stem_c, choices_c = _fallback_with_filtered_words(words, anchor.number)
            stem_d, choices_d = _fallback_with_text_block_raw(page, bbox, anchor.number)
            stem_selected, choices_selected = stem_a, choices_a
            method = "pymupdf_text"
            option_alignment_conflict = _choice_alignment_conflict(choices_a, choices_c)

            if option_alignment_low_confidence or _score_candidate(stem_c, choices_c) > _score_candidate(stem_a, choices_a):
                if _score_candidate(stem_c, choices_c) > _score_candidate(stem_a, choices_a):
                    stem_selected, choices_selected = stem_c, choices_c
                    method = "pymupdf_text_parse_choices"
            if _score_candidate(stem_d, choices_d) > _score_candidate(stem_selected, choices_selected):
                stem_selected, choices_selected = stem_d, choices_d
                method = "pymupdf_text_block_raw"

            if (
                plumber_doc is not None
                and drop_stats["dropped_visual_overlap"] == 0
                and _score_candidate(stem_selected, choices_selected) < 20
            ):
                stem_b, choices_b = _fallback_with_pdfplumber(plumber_doc.pages[anchor.page_index], bbox, anchor.number)
                candidate_score = _score_candidate(stem_b, choices_b)
                if candidate_score > _score_candidate(stem_selected, choices_selected):
                    # Keep pdfplumber fallback gated behind a character-health check.
                    stem_probe, stem_probe_quality = _normalize_text_quality(stem_b, context="stem")
                    choice_probe_payload = [
                        _normalize_text_quality(choices_b.get(label, ""), context="choice") for label in OPTION_LABELS
                    ]
                    probe_illegal = stem_probe_quality["illegal_char_count"] + sum(
                        int(meta["illegal_char_count"]) for _txt, meta in choice_probe_payload
                    )
                    probe_total_chars = max(
                        1,
                        len(stem_probe) + sum(len(txt) for txt, _meta in choice_probe_payload),
                    )
                    illegal_ratio = probe_illegal / probe_total_chars
                    if illegal_ratio <= 0.03:
                        stem_selected, choices_selected = stem_b, choices_b
                        method = "pdfplumber_text"

            stem_selected = _strip_visual_leakage_text(stem_selected)
            choices_selected = {
                label: _clear_visual_option_token(
                    stem_text=stem_selected,
                    choice_text=_strip_choice_fragment_noise(_strip_visual_leakage_text(choices_selected.get(label, ""))),
                )
                for label in OPTION_LABELS
            }

            stem_raw = collapse_inline(stem_selected)
            stem_text, stem_quality = _normalize_text_quality(stem_raw, context="stem")
            choice_meta_by_label: dict[str, dict[str, Any]] = {}
            choices_payload: list[dict[str, str]] = []
            for label in OPTION_LABELS:
                choice_raw = collapse_inline(choices_selected.get(label, ""))
                choice_text, choice_quality = _normalize_text_quality(choice_raw, context="choice")
                choice_meta_by_label[label] = choice_quality
                choices_payload.append({"label": label, "text": choice_text, "text_raw": choice_raw})

            total_char_count = max(
                1,
                len(stem_text) + sum(len(choice["text"]) for choice in choices_payload),
            )
            illegal_char_count = int(stem_quality["illegal_char_count"]) + sum(
                int(choice_meta_by_label[label]["illegal_char_count"]) for label in OPTION_LABELS
            )
            illegal_char_ratio = illegal_char_count / total_char_count
            footer_noise_detected = bool(
                FOOTER_NOISE_RE.search(stem_text)
                or any(FOOTER_NOISE_RE.search(choice["text"]) for choice in choices_payload)
                or drop_stats["dropped_noise_token"] > 0
            )
            image_text_leak_suspected = bool(
                _has_visual_leakage_pattern(stem_text)
                or any(_has_visual_leakage_pattern(choice["text"]) for choice in choices_payload)
            )
            semantic_score = _semantic_readability_score(stem_text, {c["label"]: c["text"] for c in choices_payload})
            normalization_edits = list(stem_quality["normalization_edits"])
            for label in OPTION_LABELS:
                normalization_edits.extend(choice_meta_by_label[label]["normalization_edits"])
            suspicious_tokens = sorted(
                set(stem_quality["suspicious_tokens"]).union(
                    *(set(choice_meta_by_label[label]["suspicious_tokens"]) for label in OPTION_LABELS)
                )
            )
            has_live_suspicious = _has_live_suspicious_token(stem_text) or any(
                _has_live_suspicious_token(choice["text"]) for choice in choices_payload
            )
            risk_flags: list[str] = []
            if footer_noise_detected:
                risk_flags.append("footer_noise_detected")
                summary["footer_noise_detected_count"] += 1
            if image_text_leak_suspected:
                risk_flags.append("image_text_leak_suspected")
                summary["image_text_leak_suspected_count"] += 1
            all_choices_empty = all(not collapse_inline(choice["text"]) for choice in choices_payload)
            non_empty_choice_count = sum(1 for choice in choices_payload if collapse_inline(choice["text"]))
            visual_hint_text = " ".join(
                [stem_text, *[choice["text"] for choice in choices_payload]]
            )
            visual_hint_compact = re.sub(r"\s+", "", visual_hint_text).lower()
            has_visual_hint = bool(VISUAL_HINT_RE.search(visual_hint_text)) or any(
                token in visual_hint_compact
                for token in (
                    "shownbelow",
                    "shownon",
                    "figure",
                    "diagram",
                    "picture",
                    "piece",
                    "missing",
                    "card",
                    "shape",
                    "grid",
                )
            )
            if (
                option_alignment_low_confidence
                and non_empty_choice_count <= 2
                and not (all_choices_empty and bool(stem_text))
                and drop_stats["dropped_visual_overlap"] < 6
                and not has_visual_hint
            ):
                risk_flags.append("option_alignment_low_confidence")
                summary["option_alignment_low_confidence_count"] += 1
            if option_alignment_conflict:
                risk_flags.append("option_alignment_conflict")
                summary["option_alignment_conflict_count"] += 1
            if illegal_char_count > 0:
                risk_flags.append("illegal_characters_detected")
            if suspicious_tokens and has_live_suspicious:
                risk_flags.append("suspicious_tokens_detected")
                summary["suspicious_text_question_count"] += 1
            if semantic_score < 0.25:
                risk_flags.append("semantic_readability_low")
            if risk_flags:
                summary["high_risk_question_count"] += 1
            summary["normalization_edit_count"] += len(normalization_edits)
            summary["total_illegal_char_count"] += illegal_char_count
            summary["max_illegal_char_ratio"] = max(summary["max_illegal_char_ratio"], round(illegal_char_ratio, 4))

            questions.append(
                {
                    "id": f"q{anchor.number:02d}",
                    "number": anchor.number,
                    "stem_text": stem_text,
                    "stem_text_raw": stem_raw,
                    "choices": choices_payload,
                    "quality": {
                        "footer_noise_detected": footer_noise_detected,
                        "image_text_leak_suspected": image_text_leak_suspected,
                        "option_alignment_low_confidence": option_alignment_low_confidence,
                        "option_alignment_conflict": option_alignment_conflict,
                        "semantic_readability_score": semantic_score,
                        "normalization_edits": normalization_edits,
                        "suspicious_tokens": suspicious_tokens,
                        "illegal_char_count": illegal_char_count,
                        "illegal_char_ratio": round(illegal_char_ratio, 4),
                        "risk_flags": risk_flags,
                        "dropped_token_stats": {
                            **drop_stats,
                            "dropped_by_charset_rule": illegal_char_count,
                        },
                    },
                    "source": {
                        "page": anchor.page_index + 1,
                        "text_bbox": round_rect(bbox),
                        "method": method,
                        "consensus_method": "split_words_vs_block_parse",
                    },
                }
            )
    finally:
        doc.close()
        if plumber_doc is not None:
            plumber_doc.close()

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exam_id": build_exam_id(document),
        "year": document.year,
        "family": document.family,
        "level": document.level,
        "language": document.language,
        "source_pdf": source_pdf.as_posix(),
        "question_count": len(questions),
        "questions": questions,
        "quality_summary": summary,
    }
    payload["blocking_errors"] = evaluate_text_only_blocking_errors(payload)
    return payload


def write_text_only_exam_json(output_path: Path | str, payload: dict[str, Any]) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
