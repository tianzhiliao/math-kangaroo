from __future__ import annotations

import html
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageDraw, ImageFilter

OPTION_LABELS = ("A", "B", "C", "D", "E")
OPTION_MARKER_RE = re.compile(r"^\(?([A-E])[\),.]?(?:[il])?$")
SEMANTIC_TEXT_RE = re.compile(r"[A-Za-z0-9]")
QUESTION_WORD_RE = re.compile(r"^(\d{1,2})\.$")
DRAWING_ONLY_PREFER_SVG_FAMILIES = {"canada_gr0102e_18"}

FAMILY_PROFILES: dict[str, dict[str, float]] = {
    "canada_gr0102e_18": {
        "scale": 3.0,
        "merge_gap": 10.0,
        "stem_gap": 24.0,
        "row_above": 92.0,
        "row_below": 62.0,
        "content_below": 60.0,
        "min_width": 3.0,
        "min_height": 3.0,
        "min_area": 10.0,
        "tiny_width": 18.0,
        "tiny_height": 18.0,
        "tiny_area": 80.0,
    },
    "felix_austria_15": {
        "scale": 3.0,
        "merge_gap": 9.0,
        "stem_gap": 20.0,
        "row_above": 78.0,
        "row_below": 54.0,
        "content_below": 28.0,
        "min_width": 2.5,
        "min_height": 2.5,
        "min_area": 8.0,
        "tiny_width": 16.0,
        "tiny_height": 16.0,
        "tiny_area": 70.0,
    },
    "felix_austria_16": {
        "scale": 3.0,
        "merge_gap": 9.0,
        "stem_gap": 20.0,
        "row_above": 78.0,
        "row_below": 54.0,
        "content_below": 28.0,
        "min_width": 2.5,
        "min_height": 2.5,
        "min_area": 8.0,
        "tiny_width": 16.0,
        "tiny_height": 16.0,
        "tiny_area": 70.0,
    },
    "felix_brazil_24": {
        "scale": 3.0,
        "merge_gap": 4.0,
        "stem_gap": 20.0,
        "row_above": 110.0,
        "row_below": 60.0,
        "content_below": 60.0,
        "min_width": 3.0,
        "min_height": 3.0,
        "min_area": 10.0,
        "tiny_width": 18.0,
        "tiny_height": 18.0,
        "tiny_area": 80.0,
    },
}


@dataclass(frozen=True)
class VisualCandidate:
    source: str
    rect: fitz.Rect


@dataclass
class VisualGroup:
    rect: fitz.Rect
    members: list[VisualCandidate]


@dataclass(frozen=True)
class WordToken:
    text: str
    rect: fitz.Rect


@dataclass(frozen=True)
class OptionRow:
    y0: float
    y1: float
    labels: list[tuple[str, fitz.Rect]]


def collapse_inline(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def round_rect(rect: fitz.Rect | tuple[float, float, float, float]) -> list[float]:
    if isinstance(rect, fitz.Rect):
        values = [rect.x0, rect.y0, rect.x1, rect.y1]
    else:
        values = list(rect)
    return [round(value, 2) for value in values]


def clean_generated_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def relative_href(from_path: Path, target_path: Path) -> str:
    return Path(os.path.relpath(target_path, from_path.parent)).as_posix()


def build_page_visual_cache(doc: fitz.Document) -> dict[int, dict[str, list[fitz.Rect]]]:
    cache: dict[int, dict[str, list[fitz.Rect]]] = {}
    for page_index, page in enumerate(doc):
        image_rects: list[fitz.Rect] = []
        for image in page.get_images(full=True):
            xref = image[0]
            for rect in page.get_image_rects(xref):
                image_rects.append(fitz.Rect(rect))

        try:
            drawing_clusters = [fitz.Rect(rect) for rect in page.cluster_drawings()]
        except Exception:
            drawing_clusters = []

        cache[page_index] = {
            "images": image_rects,
            "drawings": drawing_clusters,
        }
    return cache


def choice_has_semantic_text(text: str) -> bool:
    compact = collapse_inline(text)
    if compact.lower() in {"i", "l"}:
        return False
    return bool(SEMANTIC_TEXT_RE.search(compact))


def _profile(family: str) -> dict[str, float]:
    return FAMILY_PROFILES.get(family, FAMILY_PROFILES["felix_austria_15"])


def _rect_center(rect: fitz.Rect) -> tuple[float, float]:
    return ((rect.x0 + rect.x1) / 2.0, (rect.y0 + rect.y1) / 2.0)


def _rect_distance(a: fitz.Rect, b: fitz.Rect) -> float:
    if a.intersects(b):
        return 0.0
    dx = max(b.x0 - a.x1, a.x0 - b.x1, 0.0)
    dy = max(b.y0 - a.y1, a.y0 - b.y1, 0.0)
    return max(dx, dy)


def _rect_area(rect: fitz.Rect) -> float:
    return max(0.0, rect.width) * max(0.0, rect.height)


def _overlap_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
    intersection = fitz.Rect(a) & b
    if intersection.is_empty:
        return 0.0
    return _rect_area(intersection) / max(1.0, min(_rect_area(a), _rect_area(b)))


def _clamp_rect(rect: fitz.Rect, page_rect: fitz.Rect, padding: float = 1.4) -> fitz.Rect:
    return fitz.Rect(
        max(page_rect.x0, rect.x0 - padding),
        max(page_rect.y0, rect.y0 - padding),
        min(page_rect.x1, rect.x1 + padding),
        min(page_rect.y1, rect.y1 + padding),
    )


def _union_rects(rects: list[fitz.Rect]) -> fitz.Rect:
    rect = fitz.Rect(rects[0])
    for other in rects[1:]:
        rect |= other
    return rect


def _strip_token(text: str) -> str:
    return re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", text)


def _token_has_alpha(text: str) -> bool:
    return any(character.isalpha() for character in _strip_token(text))


def _group_words_into_rows(words: list[WordToken], tolerance: float = 4.0) -> list[list[WordToken]]:
    rows: list[list[WordToken]] = []
    for word in sorted(words, key=lambda item: (item.rect.y0, item.rect.x0)):
        if rows and abs(rows[-1][0].rect.y0 - word.rect.y0) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda item: item.rect.x0)
    return rows


def _row_is_prose(row: list[WordToken]) -> bool:
    cleaned_tokens = [
        _strip_token(item.text)
        for item in row
        if _strip_token(item.text) and not OPTION_MARKER_RE.match(collapse_inline(item.text))
    ]
    alpha_tokens = [token for token in cleaned_tokens if any(character.isalpha() for character in token)]
    alpha_chars = sum(sum(character.isalpha() for character in token) for token in cleaned_tokens)
    span = row[-1].rect.x1 - row[0].rect.x0 if row else 0.0
    if len(alpha_tokens) >= 3:
        return True
    if alpha_chars >= 14:
        return True
    if len(alpha_tokens) >= 2 and span >= 110.0:
        return True
    if alpha_chars >= 8 and len(cleaned_tokens) >= 4:
        return True
    return False


def _preserve_alpha_token(token: str, row: list[WordToken]) -> bool:
    cleaned = _strip_token(token)
    if not cleaned:
        return False
    row_span = row[-1].rect.x1 - row[0].rect.x0 if row else 0.0
    if len(cleaned) == 1 and cleaned.upper() == cleaned:
        return True
    if len(cleaned) <= 2 and cleaned.upper() == cleaned and len(row) <= 2 and row_span <= 80.0:
        return True
    if len(cleaned) <= 4 and cleaned.upper() == cleaned and len(row) <= 2 and row_span <= 48.0:
        return True
    return False


def _collect_question_words(page: fitz.Page, bbox: fitz.Rect) -> list[WordToken]:
    return [
        WordToken(text=text, rect=fitz.Rect(x0, y0, x1, y1))
        for x0, y0, x1, y1, text, *_ in page.get_text("words", clip=bbox)
    ]


def _build_mask_rects(words: list[WordToken], question_number: int) -> tuple[list[fitz.Rect], list[dict[str, Any]]]:
    mask_rects: list[fitz.Rect] = []
    audit: list[dict[str, Any]] = []
    for row in _group_words_into_rows(words):
        option_row = any(OPTION_MARKER_RE.match(collapse_inline(item.text)) for item in row)
        prose_row = _row_is_prose(row)
        for word in row:
            token = collapse_inline(word.text)
            cleaned = _strip_token(token)
            reason = None
            if QUESTION_WORD_RE.match(token):
                reason = "question_number"
            elif token == f"{question_number}.":
                reason = "question_number"
            elif OPTION_MARKER_RE.match(token):
                reason = "option_label"
            elif option_row and cleaned and (any(character.isdigit() for character in cleaned) or _token_has_alpha(token)):
                reason = "option_text"
            elif prose_row:
                reason = "prose_row"
            elif _token_has_alpha(token) and not _preserve_alpha_token(token, row):
                reason = "alpha_token"
            if reason is None:
                continue
            rect = fitz.Rect(word.rect)
            rect.x0 -= 1.2
            rect.y0 -= 1.0
            rect.x1 += 1.2
            rect.y1 += 1.0
            mask_rects.append(rect)
            audit.append({"text": token, "rect": round_rect(rect), "reason": reason})
    return mask_rects, audit


def _pdf_rect_to_image_box(rect: fitz.Rect, question_bbox: fitz.Rect, scale: float) -> tuple[int, int, int, int]:
    x0 = max(0, int((rect.x0 - question_bbox.x0) * scale))
    y0 = max(0, int((rect.y0 - question_bbox.y0) * scale))
    x1 = max(x0 + 1, int((rect.x1 - question_bbox.x0) * scale))
    y1 = max(y0 + 1, int((rect.y1 - question_bbox.y0) * scale))
    return x0, y0, x1, y1


def _image_box_to_pdf_rect(box: tuple[int, int, int, int], question_bbox: fitz.Rect, scale: float) -> fitz.Rect:
    x0, y0, x1, y1 = box
    return fitz.Rect(
        question_bbox.x0 + (x0 / scale),
        question_bbox.y0 + (y0 / scale),
        question_bbox.x0 + (x1 / scale),
        question_bbox.y0 + (y1 / scale),
    )


def _build_render_context(
    page: fitz.Page,
    question_bbox: fitz.Rect,
    mask_rects: list[fitz.Rect],
    scale: float,
) -> dict[str, Any]:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=question_bbox, alpha=False)
    base_image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    masked_image = base_image.copy()
    draw = ImageDraw.Draw(masked_image)
    for rect in mask_rects:
        draw.rectangle(_pdf_rect_to_image_box(rect, question_bbox, scale), fill=(255, 255, 255))
    ink = masked_image.convert("L").point(lambda pixel: 255 if pixel < 232 else 0)
    ink = ink.filter(ImageFilter.MaxFilter(3))
    return {
        "scale": scale,
        "base_image": base_image,
        "masked_image": masked_image,
        "ink": ink,
        "mask_rects": mask_rects,
    }


def _trim_image_region(ink: Image.Image, region: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    cropped = ink.crop(region)
    bbox = cropped.getbbox()
    if bbox is None:
        return None
    return (
        region[0] + bbox[0],
        region[1] + bbox[1],
        region[0] + bbox[2],
        region[1] + bbox[3],
    )


def _axis_spans(
    ink: Image.Image,
    region: tuple[int, int, int, int],
    axis: str,
    blank_tolerance: int = 1,
    min_span: int = 2,
) -> list[tuple[int, int, int, int]]:
    x0, y0, x1, y1 = region
    limit = (y1 - y0) if axis == "y" else (x1 - x0)
    spans: list[tuple[int, int, int, int]] = []
    start: int | None = None
    blanks = 0

    for offset in range(limit):
        if axis == "y":
            strip = (x0, y0 + offset, x1, y0 + offset + 1)
        else:
            strip = (x0 + offset, y0, x0 + offset + 1, y1)
        occupied = ink.crop(strip).getbbox() is not None
        if occupied:
            if start is None:
                start = offset
            blanks = 0
            continue
        if start is None:
            continue
        blanks += 1
        if blanks > blank_tolerance:
            end = offset - blanks + 1
            if end - start >= min_span:
                if axis == "y":
                    spans.append((x0, y0 + start, x1, y0 + end))
                else:
                    spans.append((x0 + start, y0, x0 + end, y1))
            start = None
            blanks = 0

    if start is not None:
        end = limit
        if end - start >= min_span:
            if axis == "y":
                spans.append((x0, y0 + start, x1, y0 + end))
            else:
                spans.append((x0 + start, y0, x0 + end, y1))
    return spans


def _split_ink_regions(ink: Image.Image, region: tuple[int, int, int, int]) -> list[tuple[int, int, int, int]]:
    trimmed = _trim_image_region(ink, region)
    if trimmed is None:
        return []
    row_spans = _axis_spans(ink, trimmed, axis="y")
    if len(row_spans) > 1:
        regions: list[tuple[int, int, int, int]] = []
        for row_span in row_spans:
            regions.extend(_split_ink_regions(ink, row_span))
        return regions
    column_spans = _axis_spans(ink, trimmed, axis="x")
    if len(column_spans) > 1:
        regions = []
        for column_span in column_spans:
            regions.extend(_split_ink_regions(ink, column_span))
        return regions
    return [trimmed]


def _extract_render_candidates(
    page: fitz.Page,
    question_bbox: fitz.Rect,
    render_context: dict[str, Any],
    family: str,
) -> list[VisualCandidate]:
    profile = _profile(family)
    root = render_context["ink"].getbbox()
    if root is None:
        return []
    scale = float(render_context["scale"])
    candidates: list[VisualCandidate] = []
    for region in _split_ink_regions(render_context["ink"], root):
        rect = _image_box_to_pdf_rect(region, question_bbox, scale)
        rect = _clamp_rect(rect, page.rect, padding=0.8)
        if rect.width >= question_bbox.width * 0.78 and rect.height <= 6.0:
            continue
        if rect.height >= question_bbox.height * 0.78 and rect.width <= 6.0:
            continue
        if rect.width < profile["min_width"] and rect.height < profile["min_height"]:
            continue
        if _rect_area(rect) < profile["min_area"]:
            continue
        candidates.append(VisualCandidate(source="render", rect=rect))
    return candidates


def _is_noise_drawing(rect: fitz.Rect, question_bbox: fitz.Rect) -> bool:
    if rect.width <= 2.0 and rect.height <= 2.0:
        return True
    if rect.width >= question_bbox.width * 0.8 and rect.height <= 6.0:
        return True
    if rect.height >= question_bbox.height * 0.8 and rect.width <= 6.0:
        return True
    if rect.width >= question_bbox.width * 0.85 and rect.height >= question_bbox.height * 0.18:
        return True
    return False


def _collect_hint_candidates(
    question_bbox: fitz.Rect,
    page_rect: fitz.Rect,
    visual_cache: dict[str, list[fitz.Rect]],
) -> list[VisualCandidate]:
    raw: list[VisualCandidate] = []
    for rect in visual_cache["images"]:
        if not rect.intersects(question_bbox):
            continue
        clipped = _clamp_rect(fitz.Rect(rect) & question_bbox, page_rect, padding=0.6)
        if clipped.width < 8.0 or clipped.height < 8.0:
            continue
        raw.append(VisualCandidate(source="image", rect=clipped))

    for rect in visual_cache["drawings"]:
        if not rect.intersects(question_bbox):
            continue
        clipped = _clamp_rect(fitz.Rect(rect) & question_bbox, page_rect, padding=0.6)
        if _is_noise_drawing(clipped, question_bbox):
            continue
        raw.append(VisualCandidate(source="drawing", rect=clipped))
    return raw


def _dedupe_candidates(candidates: list[VisualCandidate]) -> list[VisualCandidate]:
    kept: list[VisualCandidate] = []
    for candidate in sorted(candidates, key=lambda item: _rect_area(item.rect), reverse=True):
        if any(_overlap_ratio(candidate.rect, other.rect) >= 0.88 for other in kept):
            continue
        kept.append(candidate)
    kept.sort(key=lambda item: (item.rect.y0, item.rect.x0))
    return kept


def _merge_candidates(candidates: list[VisualCandidate], gap: float) -> list[VisualGroup]:
    if not candidates:
        return []
    groups = [VisualGroup(rect=fitz.Rect(candidate.rect), members=[candidate]) for candidate in candidates]
    changed = True
    while changed:
        changed = False
        merged: list[VisualGroup] = []
        while groups:
            group = groups.pop(0)
            index = 0
            while index < len(groups):
                other = groups[index]
                if _rect_distance(group.rect, other.rect) <= gap:
                    group.rect |= other.rect
                    group.members.extend(other.members)
                    groups.pop(index)
                    changed = True
                    continue
                index += 1
            merged.append(group)
        groups = merged
    groups.sort(key=lambda item: (item.rect.y0, item.rect.x0))
    return groups


def _collect_option_rows(page: fitz.Page, bbox: fitz.Rect) -> list[OptionRow]:
    markers: list[tuple[str, fitz.Rect, bool]] = []
    for x0, y0, x1, y1, text, *_ in page.get_text("words", clip=bbox):
        token = collapse_inline(text)
        match = OPTION_MARKER_RE.match(token)
        if not match:
            continue
        explicit = any(character in token for character in "()[]).")
        markers.append((match.group(1), fitz.Rect(x0, y0, x1, y1), explicit))
    markers.sort(key=lambda item: (item[1].y0, item[1].x0))
    rows: list[list[tuple[str, fitz.Rect, bool]]] = []
    for label, rect, explicit in markers:
        if rows and abs(rows[-1][0][1].y0 - rect.y0) <= 8.0:
            rows[-1].append((label, rect, explicit))
        else:
            rows.append([(label, rect, explicit)])
    option_rows: list[OptionRow] = []
    for row in rows:
        row.sort(key=lambda item: item[1].x0)
        merged: list[tuple[str, fitz.Rect, bool]] = []
        for label, rect, explicit in row:
            if merged and merged[-1][0] == label and abs(merged[-1][1].x1 - rect.x0) <= 12.0:
                combined = fitz.Rect(merged[-1][1])
                combined |= rect
                merged[-1] = (label, combined, merged[-1][2] or explicit)
            else:
                merged.append((label, rect, explicit))
        if len(merged) < 2 and not any(explicit for _label, _rect, explicit in merged):
            continue
        option_rows.append(
            OptionRow(
                y0=min(rect.y0 for _, rect, _explicit in merged),
                y1=max(rect.y1 for _, rect, _explicit in merged),
                labels=[(label, rect) for label, rect, _explicit in merged],
            )
        )
    return option_rows


def _stem_text_bottom(page: fitz.Page, bbox: fitz.Rect, option_rows: list[OptionRow], question_number: int) -> float:
    cutoff = option_rows[0].y0 - 2.0 if option_rows else bbox.y1 + 1.0
    bottom = bbox.y0
    for x0, y0, x1, y1, text, *_ in page.get_text("words", clip=bbox):
        token = collapse_inline(text)
        if token == f"{question_number}." or OPTION_MARKER_RE.match(token):
            continue
        if y0 >= cutoff:
            continue
        bottom = max(bottom, y1)
    return bottom


def _label_x_limit(row: OptionRow, index: int) -> float:
    centers = [(_rect_center(rect)[0]) for _, rect in row.labels]
    center = centers[index]
    neighbor_distances: list[float] = []
    if index > 0:
        neighbor_distances.append(center - centers[index - 1])
    if index + 1 < len(centers):
        neighbor_distances.append(centers[index + 1] - center)
    if neighbor_distances:
        return max(26.0, min(84.0, min(neighbor_distances) * 0.58))
    return 52.0


def _best_option_label(
    group: VisualGroup,
    option_rows: list[OptionRow],
    question_bbox: fitz.Rect,
    family: str,
) -> tuple[str | None, float]:
    profile = _profile(family)
    group_center_x, group_center_y = _rect_center(group.rect)
    best_label = None
    best_score = -1e9
    for row in option_rows:
        if group_center_y < row.y0 - profile["row_above"]:
            continue
        if group_center_y > row.y1 + profile["row_below"]:
            continue
        if group.rect.y1 < row.y0 - 6.0:
            continue
        if group.rect.width >= question_bbox.width * 0.54 and len(row.labels) >= 3:
            continue
        for index, (label, rect) in enumerate(row.labels):
            label_center_x, label_center_y = _rect_center(rect)
            horizontal_distance = abs(group_center_x - label_center_x)
            if horizontal_distance > _label_x_limit(row, index):
                continue
            vertical_distance = abs(group_center_y - label_center_y)
            score = 100.0 - horizontal_distance - (vertical_distance * 0.45)
            if group.rect.x0 <= label_center_x <= group.rect.x1:
                score += 12.0
            if group.rect.y0 <= label_center_y <= group.rect.y1 + 10.0:
                score += 6.0
            if score > best_score:
                best_score = score
                best_label = label
    return best_label, best_score


def _group_is_tiny(group: VisualGroup, family: str) -> bool:
    profile = _profile(family)
    return (
        group.rect.width <= profile["tiny_width"]
        and group.rect.height <= profile["tiny_height"]
        and _rect_area(group.rect) <= profile["tiny_area"]
    )


def _merge_assigned_groups(groups: list[VisualGroup], gap: float) -> list[VisualGroup]:
    candidates = [
        VisualCandidate(source=member.source, rect=fitz.Rect(member.rect))
        for group in groups
        for member in group.members
    ]
    return _merge_candidates(candidates, gap)


def _fallback_option_rect(
    render_context: dict[str, Any],
    question_bbox: fitz.Rect,
    option_row: OptionRow,
    label_index: int,
    stem_text_bottom: float,
) -> fitz.Rect | None:
    label, rect = option_row.labels[label_index]
    _ = label
    left = rect.x0 - 8.0
    right = rect.x1 + 8.0
    if label_index > 0:
        previous_center = _rect_center(option_row.labels[label_index - 1][1])[0]
        current_center = _rect_center(rect)[0]
        left = (previous_center + current_center) / 2.0
    if label_index + 1 < len(option_row.labels):
        current_center = _rect_center(rect)[0]
        next_center = _rect_center(option_row.labels[label_index + 1][1])[0]
        right = (current_center + next_center) / 2.0

    def zone_ink_ratio(zone: fitz.Rect) -> tuple[float, tuple[int, int, int, int] | None]:
        clipped = fitz.Rect(zone) & question_bbox
        if clipped.is_empty or clipped.width <= 4.0 or clipped.height <= 4.0:
            return 0.0, None
        image_box = _pdf_rect_to_image_box(clipped, question_bbox, float(render_context["scale"]))
        cropped = render_context["ink"].crop(image_box)
        bbox = cropped.getbbox()
        if bbox is None:
            return 0.0, None
        non_zero = cropped.histogram()[255]
        total = max(1, cropped.size[0] * cropped.size[1])
        return non_zero / total, (
            image_box[0] + bbox[0],
            image_box[1] + bbox[1],
            image_box[0] + bbox[2],
            image_box[1] + bbox[3],
        )

    inline_zone = fitz.Rect(
        rect.x1 + 2.0,
        max(stem_text_bottom + 4.0, rect.y0 - 8.0),
        right,
        min(question_bbox.y1, rect.y1 + 10.0),
    )
    above_zone = fitz.Rect(
        left,
        max(stem_text_bottom + 4.0, rect.y0 - 48.0),
        right,
        max(stem_text_bottom + 8.0, rect.y0 - 4.0),
    )
    below_zone = fitz.Rect(
        left,
        min(question_bbox.y1 - 4.0, rect.y1 + 4.0),
        right,
        min(question_bbox.y1, rect.y1 + 52.0),
    )

    inline_ratio, inline_box = zone_ink_ratio(inline_zone)
    if inline_ratio >= 0.003 and inline_box is not None:
        return _image_box_to_pdf_rect(inline_box, question_bbox, float(render_context["scale"]))

    ranked = []
    for zone in (above_zone, below_zone):
        ratio, box = zone_ink_ratio(zone)
        if box is not None:
            ranked.append((ratio, box))
    if not ranked:
        return None
    best_box = max(ranked, key=lambda item: item[0])[1]
    return _image_box_to_pdf_rect(best_box, question_bbox, float(render_context["scale"]))


def _option_slot_rect(
    question_bbox: fitz.Rect,
    option_rows: list[OptionRow],
    row_index: int,
    label_index: int,
    stem_text_bottom: float,
) -> fitz.Rect:
    row = option_rows[row_index]
    centers = [_rect_center(rect)[0] for _, rect in row.labels]
    row_centers = [(_rect_center(item.labels[0][1])[1] + _rect_center(item.labels[-1][1])[1]) / 2.0 for item in option_rows]

    label_rect = row.labels[label_index][1]
    left = label_rect.x0 - 12.0
    right = label_rect.x1 + 12.0
    if label_index > 0:
        left = (centers[label_index - 1] + centers[label_index]) / 2.0
    elif len(centers) > 1:
        left = centers[label_index] - min(92.0, (centers[label_index + 1] - centers[label_index]) * 0.75)
    if label_index + 1 < len(centers):
        right = (centers[label_index] + centers[label_index + 1]) / 2.0
    elif len(centers) > 1:
        right = centers[label_index] + min(92.0, (centers[label_index] - centers[label_index - 1]) * 0.75)

    top = max(question_bbox.y0, stem_text_bottom + 4.0)
    bottom = question_bbox.y1
    if row_index > 0:
        top = max(top, (row_centers[row_index - 1] + row_centers[row_index]) / 2.0)
    if row_index + 1 < len(option_rows):
        bottom = min(bottom, (row_centers[row_index] + row_centers[row_index + 1]) / 2.0)

    return fitz.Rect(
        max(question_bbox.x0, left - 2.0),
        max(question_bbox.y0, top),
        min(question_bbox.x1, right + 2.0),
        min(question_bbox.y1, bottom),
    )


def _candidate_matches_slot(candidate: VisualCandidate, slot_rect: fitz.Rect) -> bool:
    if slot_rect.contains(fitz.Point(*_rect_center(candidate.rect))):
        return True
    overlap = fitz.Rect(candidate.rect) & slot_rect
    if overlap.is_empty:
        return False
    return _rect_area(overlap) / max(1.0, _rect_area(candidate.rect)) >= 0.82


def _slot_candidate_bbox(
    question_bbox: fitz.Rect,
    option_rows: list[OptionRow],
    row_index: int,
    label_index: int,
    stem_text_bottom: float,
    hint_candidates: list[VisualCandidate],
    raw_candidates: list[VisualCandidate],
) -> fitz.Rect | None:
    slot_rect = _option_slot_rect(question_bbox, option_rows, row_index, label_index, stem_text_bottom)
    hint_matches = [candidate.rect for candidate in hint_candidates if _candidate_matches_slot(candidate, slot_rect)]
    if hint_matches:
        return _union_rects(hint_matches)

    raw_matches = [candidate.rect for candidate in raw_candidates if _candidate_matches_slot(candidate, slot_rect)]
    focused = [rect for rect in raw_matches if rect.width <= slot_rect.width * 1.35 and rect.height <= slot_rect.height * 1.2]
    if focused:
        return _union_rects(focused)
    return None


def _bbox_intersects_masks(bbox: fitz.Rect, mask_rects: list[fitz.Rect]) -> bool:
    return any(fitz.Rect(bbox).intersects(mask_rect) for mask_rect in mask_rects)


def _bbox_hits_images(bbox: fitz.Rect, image_rects: list[fitz.Rect]) -> bool:
    return any(_overlap_ratio(bbox, image_rect) >= 0.12 for image_rect in image_rects if bbox.intersects(image_rect))


def _snap_bbox_to_image_hints(
    bbox: fitz.Rect,
    question_bbox: fitz.Rect,
    image_rects: list[fitz.Rect],
    page_rect: fitz.Rect,
) -> fitz.Rect:
    center_x, center_y = _rect_center(bbox)
    candidates = [
        rect
        for rect in image_rects
        if rect.intersects(bbox)
        and (_rect_area(fitz.Rect(rect) & question_bbox) / max(1.0, _rect_area(rect))) >= 0.72
        and (_overlap_ratio(bbox, rect) >= 0.16 or rect.contains(fitz.Point(center_x, center_y)))
    ]
    if not candidates:
        return bbox
    best = max(candidates, key=_rect_area)
    if _rect_area(best) <= _rect_area(bbox) * 1.08:
        return bbox
    if _rect_area(best) >= _rect_area(bbox) * 8.0:
        return bbox
    return _clamp_rect(best, page_rect, padding=1.0)


def _export_svg_clip(page: fitz.Page, bbox: fitz.Rect) -> str:
    original_crop = fitz.Rect(page.cropbox)
    page.set_cropbox(bbox)
    try:
        return page.get_svg_image(text_as_path=1)
    finally:
        page.set_cropbox(original_crop)


def _export_masked_png(
    masked_image: Image.Image,
    question_bbox: fitz.Rect,
    scale: float,
    bbox: fitz.Rect,
    asset_path: Path,
) -> None:
    crop = masked_image.crop(_pdf_rect_to_image_box(bbox, question_bbox, scale))
    crop.save(asset_path.as_posix())


def _export_asset(
    page: fitz.Page,
    question_bbox: fitz.Rect,
    render_context: dict[str, Any],
    visual_cache: dict[str, list[fitz.Rect]],
    bbox: fitz.Rect,
    asset_id: str,
    role: str,
    assets_dir: Path,
    family: str,
    year: int | None,
) -> dict[str, Any]:
    bbox = _snap_bbox_to_image_hints(bbox, question_bbox, visual_cache["images"], page.rect)
    masked_intersection = _bbox_intersects_masks(bbox, render_context["mask_rects"])
    image_backed = _bbox_hits_images(bbox, visual_cache["images"])
    prefer_svg = not masked_intersection and not image_backed

    if prefer_svg:
        asset_path = assets_dir / f"{asset_id}.svg"
        asset_path.write_text(_export_svg_clip(page, bbox), encoding="utf-8")
        asset_format = "svg"
    elif masked_intersection:
        asset_path = assets_dir / f"{asset_id}.png"
        _export_masked_png(
            render_context["masked_image"],
            question_bbox,
            float(render_context["scale"]),
            bbox,
            asset_path,
        )
        asset_format = "png"
    else:
        asset_path = assets_dir / f"{asset_id}.png"
        page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=bbox, alpha=False).save(asset_path.as_posix())
        asset_format = "png"

    return {
        "id": asset_id,
        "path": asset_path.relative_to(assets_dir.parent).as_posix(),
        "kind": "question_figure",
        "format": asset_format,
        "page": page.number + 1,
        "bbox": round_rect(bbox),
        "role": role,
    }


def extract_question_visual_assets(
    family: str,
    year: int | None,
    page: fitz.Page,
    question_number: int,
    question_bbox: fitz.Rect,
    choices: list[dict[str, Any]],
    visual_cache: dict[str, list[fitz.Rect]],
    assets_dir: Path,
) -> dict[str, Any]:
    profile = _profile(family)
    words = _collect_question_words(page, question_bbox)
    mask_rects, mask_audit = _build_mask_rects(words, question_number)
    render_context = _build_render_context(page, question_bbox, mask_rects, profile["scale"])
    option_rows = _collect_option_rows(page, question_bbox)
    stem_text_bottom = _stem_text_bottom(page, question_bbox, option_rows, question_number)
    needs_option_assets = {
        choice["label"]: not choice_has_semantic_text(choice["text"])
        for choice in choices
    }
    content_bottom = question_bbox.y1
    if option_rows:
        content_bottom = min(question_bbox.y1, option_rows[-1].y1 + profile["content_below"])

    render_candidates = _extract_render_candidates(page, question_bbox, render_context, family)
    hint_candidates = _collect_hint_candidates(question_bbox, page.rect, visual_cache)
    if option_rows:
        render_candidates = [candidate for candidate in render_candidates if candidate.rect.y0 <= content_bottom + 6.0]
        hint_candidates = [candidate for candidate in hint_candidates if candidate.rect.y0 <= content_bottom + 6.0]
    raw_candidates = _dedupe_candidates([*render_candidates, *hint_candidates])
    groups = _merge_candidates(raw_candidates, profile["merge_gap"])
    groups = [group for group in groups if group.rect.y0 <= content_bottom + 6.0]
    assignments: dict[str, list[VisualGroup]] = {"stem": []}
    for label in OPTION_LABELS:
        assignments[label] = []

    for group in groups:
        label, _score = _best_option_label(group, option_rows, question_bbox, family)
        if label is not None:
            assignments[label].append(group)
        else:
            assignments["stem"].append(group)

    if option_rows:
        remaining_stem: list[VisualGroup] = list(assignments["stem"])
        rescued: set[int] = set()
        for row in option_rows:
            row_labels = [label for label, _rect in row.labels if not assignments[label]]
            if not row_labels:
                continue
            row_candidates = [
                group
                for group in remaining_stem
                if group.rect.y1 >= stem_text_bottom - 4.0 and group.rect.y0 <= row.y1 + 10.0
            ]
            if len(row_candidates) < len(row_labels):
                continue
            ordered = sorted(row_candidates, key=lambda item: item.rect.x0)[: len(row_labels)]
            for label, group in zip(row_labels, ordered):
                assignments[label].append(group)
                rescued.add(id(group))
        if rescued:
            assignments["stem"] = [group for group in remaining_stem if id(group) not in rescued]

    assignments["stem"] = _merge_assigned_groups(assignments["stem"], profile["stem_gap"])
    if family == "canada_gr0102e_18" and len(assignments["stem"]) > 2:
        assignments["stem"] = [
            VisualGroup(
                rect=_union_rects([group.rect for group in assignments["stem"]]),
                members=[member for group in assignments["stem"] for member in group.members],
            )
        ]
    for label in OPTION_LABELS:
        if assignments[label]:
            merged = _merge_assigned_groups(assignments[label], profile["merge_gap"])
            assignments[label] = merged[:1]

    assets: list[dict[str, Any]] = []
    shared_asset_refs: list[str] = []
    option_asset_refs: dict[str, list[str]] = {label: [] for label in OPTION_LABELS}
    first_option_y0 = option_rows[0].y0 if option_rows else question_bbox.y1
    option_row_lookup = {
        label: (row_index, row, label_index)
        for row_index, row in enumerate(option_rows)
        for label_index, (label, _rect) in enumerate(row.labels)
    }
    slot_candidate_bboxes: dict[str, fitz.Rect | None] = {}
    for label, fallback_entry in option_row_lookup.items():
        row_index, _row, label_index = fallback_entry
        slot_candidate_bboxes[label] = _slot_candidate_bbox(
            question_bbox,
            option_rows,
            row_index,
            label_index,
            stem_text_bottom,
            hint_candidates,
            raw_candidates,
        )
    if all(choice_has_semantic_text(choice["text"]) for choice in choices) and (
        sum(1 for bbox in slot_candidate_bboxes.values() if bbox is not None) < 3
    ):
        slot_candidate_bboxes = {label: None for label in OPTION_LABELS}

    for stem_index, group in enumerate(assignments["stem"], start=1):
        bbox = _clamp_rect(group.rect, page.rect, padding=1.0)
        if not any(needs_option_assets.values()) and bbox.y1 > first_option_y0 - 4.0:
            bbox = fitz.Rect(bbox.x0, bbox.y0, bbox.x1, max(bbox.y0 + 4.0, first_option_y0 - 6.0))
        if _group_is_tiny(group, family):
            continue
        asset_id = f"q{question_number:02d}_stem_{stem_index:02d}"
        asset = _export_asset(
            page=page,
            question_bbox=question_bbox,
            render_context=render_context,
            visual_cache=visual_cache,
            bbox=bbox,
            asset_id=asset_id,
            role="stem",
            assets_dir=assets_dir,
            family=family,
            year=year,
        )
        assets.append(asset)
        shared_asset_refs.append(asset_id)

    for row in option_rows:
        _ = row
    for label in OPTION_LABELS:
        groups_for_label = assignments[label]
        if not groups_for_label:
            continue
        group = groups_for_label[0]
        choice = next(choice for choice in choices if choice["label"] == label)
        fallback_entry = option_row_lookup.get(label)
        bbox = slot_candidate_bboxes.get(label)
        bbox_from_slot = bbox is not None
        if not needs_option_assets.get(label, False) and not bbox_from_slot:
            continue
        if _group_is_tiny(group, family) and choice_has_semantic_text(choice["text"]) and not bbox_from_slot:
            continue
        if bbox is None:
            bbox = _clamp_rect(group.rect, page.rect, padding=0.8)
        if fallback_entry is not None and not bbox_from_slot:
            row_index, row, label_index = fallback_entry
            fallback_rect = _fallback_option_rect(render_context, question_bbox, row, label_index, stem_text_bottom)
            if fallback_rect is not None:
                fallback_rect = _clamp_rect(fallback_rect, page.rect, padding=0.8)
                fallback_area = _rect_area(fallback_rect)
                current_area = _rect_area(bbox)
                fallback_viable = (
                    fallback_area >= max(profile["min_area"] * 4.0, 80.0)
                    and fallback_rect.width >= max(profile["min_width"] * 3.0, 18.0)
                    and fallback_rect.height >= max(profile["min_height"] * 3.0, 18.0)
                )
                if fallback_area > 0 and current_area < (fallback_area * 0.45):
                    bbox = fallback_rect
                elif fallback_viable and current_area > (fallback_area * 1.8) and fallback_area >= (current_area * 0.32):
                    bbox = fallback_rect
        asset_id = f"q{question_number:02d}_option_{label}_01"
        asset = _export_asset(
            page=page,
            question_bbox=question_bbox,
            render_context=render_context,
            visual_cache=visual_cache,
            bbox=bbox,
            asset_id=asset_id,
            role="option",
            assets_dir=assets_dir,
            family=family,
            year=year,
        )
        assets.append(asset)
        option_asset_refs[label].append(asset_id)

    for row_index, row in enumerate(option_rows):
        for label_index, (label, _rect) in enumerate(row.labels):
            if option_asset_refs[label] or not needs_option_assets.get(label, False):
                continue
            slot_bbox = _slot_candidate_bbox(
                question_bbox,
                option_rows,
                row_index,
                label_index,
                stem_text_bottom,
                hint_candidates,
                raw_candidates,
            )
            fallback_rect = slot_bbox or _fallback_option_rect(
                render_context,
                question_bbox,
                row,
                label_index,
                stem_text_bottom,
            )
            if fallback_rect is None:
                continue
            fallback_rect = _clamp_rect(fallback_rect, page.rect, padding=0.8)
            if fallback_rect.width < profile["min_width"] or fallback_rect.height < profile["min_height"]:
                continue
            if _rect_area(fallback_rect) < profile["min_area"]:
                continue
            asset_id = f"q{question_number:02d}_option_{label}_01"
            asset = _export_asset(
                page=page,
                question_bbox=question_bbox,
                render_context=render_context,
                visual_cache=visual_cache,
                bbox=fallback_rect,
                asset_id=asset_id,
                role="option",
                assets_dir=assets_dir,
                family=family,
                year=year,
            )
            assets.append(asset)
            option_asset_refs[label].append(asset_id)

    return {
        "assets": assets,
        "shared_asset_refs": shared_asset_refs,
        "option_asset_refs": option_asset_refs,
        "audit": {
            "mask_rects": [round_rect(rect) for rect in mask_rects],
            "masked_tokens": mask_audit,
            "option_rows": [
                {
                    "bbox": round_rect((row.labels[0][1].x0, row.y0, row.labels[-1][1].x1, row.y1)),
                    "labels": {label: round_rect(rect) for label, rect in row.labels},
                }
                for row in option_rows
            ],
            "stem_text_bottom": round(stem_text_bottom, 2),
            "render_candidates": [round_rect(candidate.rect) for candidate in render_candidates],
            "hint_candidates": [
                {"source": candidate.source, "rect": round_rect(candidate.rect)} for candidate in hint_candidates
            ],
            "visual_candidates": [
                {
                    "rect": round_rect(group.rect),
                    "sources": sorted({member.source for member in group.members}),
                    "member_count": len(group.members),
                }
                for group in groups
            ],
            "asset_assignments": {
                "stem": [round_rect(group.rect) for group in assignments["stem"]],
                "options": {
                    label: [round_rect(group.rect) for group in assignments[label]]
                    for label in OPTION_LABELS
                    if assignments[label]
                },
            },
        },
    }


def write_asset_qa_report(
    doc: fitz.Document,
    exam_id: str,
    exam_dir: Path,
    questions: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    qa_root: Path,
) -> Path:
    qa_dir = qa_root / exam_id
    clean_generated_dir(qa_dir)
    qa_html_path = qa_root / f"{exam_id}.html"
    qa_root.mkdir(parents=True, exist_ok=True)

    asset_by_id = {asset["id"]: asset for asset in assets}
    cards: list[str] = []
    for question in questions:
        bbox = fitz.Rect(question["source"]["bbox"])
        page = doc[question["source"]["page"] - 1]
        reference_name = f"{question['id']}_reference.png"
        reference_path = qa_dir / reference_name
        page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=bbox, alpha=False).save(reference_path.as_posix())

        stem_images = [
            f'<img src="{html.escape(relative_href(qa_html_path, exam_dir / asset_by_id[asset_id]["path"]))}" alt="{asset_id}" />'
            for asset_id in question["shared_asset_refs"]
        ]
        option_blocks: list[str] = []
        for choice in question["choices"]:
            images = [
                f'<img src="{html.escape(relative_href(qa_html_path, exam_dir / asset_by_id[asset_id]["path"]))}" alt="{asset_id}" />'
                for asset_id in choice["asset_refs"]
            ]
            option_blocks.append(
                f"""
                <div class="option-card">
                  <div class="option-label">选项 {html.escape(choice['label'])}</div>
                  <div class="option-text">{html.escape(choice['text']) or "无文字"}</div>
                  <div class="image-strip">{''.join(images) or '<span class="empty">无图片</span>'}</div>
                </div>
                """
            )

        cards.append(
            f"""
            <section class="question-card" id="{html.escape(question['id'])}">
              <div class="question-head">
                <h2>第 {question['number']} 题</h2>
                <div class="meta">第 {question['source']['page']} 页 | 置信度 {question['source']['confidence']}</div>
              </div>
              <div class="grid">
                <div class="panel">
                  <h3>原题参考图</h3>
                  <img src="{html.escape(relative_href(qa_html_path, reference_path))}" alt="{question['id']} reference" />
                </div>
                <div class="panel">
                  <h3>题干图</h3>
                  <div class="image-strip">{''.join(stem_images) or '<span class="empty">无图片</span>'}</div>
                  <div class="text-block">{html.escape(question['stem_text'])}</div>
                </div>
              </div>
              <div class="options-grid">
                {''.join(option_blocks)}
              </div>
            </section>
            """
        )

    qa_html_path.write_text(
        f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(exam_id)} 题图 QA</title>
  <style>
    :root {{
      --bg: #f3efe6;
      --card: rgba(255, 255, 255, 0.88);
      --ink: #1f1a17;
      --muted: #6d665c;
      --line: rgba(31, 26, 23, 0.12);
      --accent: #0e7490;
      --shadow: 0 18px 40px rgba(31, 26, 23, 0.1);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(14, 116, 144, 0.14), transparent 28rem),
        linear-gradient(180deg, #f7f3eb 0%, var(--bg) 100%);
    }}
    main {{ width: min(1240px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0 64px; }}
    h1 {{ margin: 0 0 8px; font-size: 2rem; }}
    p.lead {{ margin: 0 0 24px; color: var(--muted); line-height: 1.7; }}
    .question-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      margin: 0 0 24px;
      box-shadow: var(--shadow);
    }}
    .question-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
      margin-bottom: 16px;
    }}
    .question-head h2 {{ margin: 0; font-size: 1.35rem; }}
    .meta {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }}
    .panel, .option-card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.82);
    }}
    .panel h3, .option-label {{
      margin: 0 0 10px;
      font-size: 1rem;
      color: var(--accent);
      font-weight: 700;
    }}
    .panel img, .option-card img {{
      display: block;
      max-width: 100%;
      max-height: 220px;
      margin: 0 auto;
      background: #fff;
      border-radius: 12px;
      border: 1px solid rgba(31, 26, 23, 0.08);
      padding: 6px;
    }}
    .image-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: flex-start;
    }}
    .text-block {{
      margin-top: 12px;
      color: var(--muted);
      line-height: 1.7;
      white-space: pre-wrap;
    }}
    .options-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 12px;
    }}
    .option-text {{
      min-height: 2.8em;
      color: var(--muted);
      line-height: 1.6;
      margin-bottom: 10px;
      white-space: pre-wrap;
    }}
    .empty {{
      color: var(--muted);
      font-style: italic;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(exam_id)} 题图核验页</h1>
    <p class="lead">这页用于逐题对照原题参考图、题干图和选项图，检查是否把无关文字、题号或其他题的内容裁进来了。</p>
    {''.join(cards)}
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return qa_html_path
