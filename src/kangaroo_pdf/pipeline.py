from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
from pypdf import PdfReader

from .asset_qa import build_asset_qa_index, build_asset_qa_page
from .diagram_assets import (
    build_page_visual_cache,
    build_page_word_cache,
    choice_requires_asset,
    extract_question_assets,
)

OPTION_LABELS = ("A", "B", "C", "D", "E")
QUESTION_WORD_RE = re.compile(r"^(\d{1,2})\.$")
INLINE_QUESTION_RE = re.compile(r"(?<!\d)(\d{1,2})\.")
OPTION_TOKEN_RE = re.compile(r"^\(?([A-E])\)?$")
NOISE_LINE_RE = re.compile(
    r"(copyright|all rights reserved|for training purposes|do not duplicate|page \d+|mathkangaroo\.ca|www\.kaenguru\.at)",
    re.IGNORECASE,
)
LEVEL_ROW_BREAK_RE = re.compile(r"^(felix|[ée]colier|benjamin|kadett|junior|student)\b", re.IGNORECASE)
FAMILY_CANADA = "canada_gr0102e_18"
FAMILY_FELIX_AT_15 = "felix_austria_15"
FAMILY_FELIX_AT_16 = "felix_austria_16"
FAMILY_FELIX_BR_24 = "felix_brazil_24"
FAMILY_ANSWERS = "answers_table_text_or_ocr"
SUPPORTED_FAMILIES = {
    FAMILY_CANADA,
    FAMILY_FELIX_AT_15,
    FAMILY_FELIX_AT_16,
    FAMILY_FELIX_BR_24,
    FAMILY_ANSWERS,
}


@dataclass(frozen=True)
class ClassifiedDocument:
    path: str
    filename: str
    family: str
    year: int | None
    level: str
    language: str
    question_count: int | None
    is_answer_table: bool
    answer_mode: str | None
    page_count: int
    pdf_title: str
    pdf_author: str


@dataclass(frozen=True)
class QuestionAnchor:
    number: int
    page_index: int
    rect: tuple[float, float, float, float]


def normalize_space(text: str) -> str:
    cleaned = text.replace("\xa0", " ").replace("\u2013", "-").replace("\u2014", "-")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s*\n\s*", "\n", cleaned)
    return cleaned.strip()


def collapse_inline(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_space(text)).strip()


def round_rect(rect: fitz.Rect | tuple[float, float, float, float]) -> list[float]:
    if isinstance(rect, fitz.Rect):
        values = [rect.x0, rect.y0, rect.x1, rect.y1]
    else:
        values = list(rect)
    return [round(value, 2) for value in values]


def read_pdf_text(path: Path) -> tuple[str, PdfReader]:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text, reader


def detect_question_sequence(text: str) -> list[int]:
    numbers = [int(token) for token in INLINE_QUESTION_RE.findall(text)]
    sequence: list[int] = []
    started = False
    expected = 1
    for number in numbers:
        if not started:
            if number == 1:
                sequence = [1]
                started = True
                expected = 2
            continue
        if number == expected:
            sequence.append(number)
            expected += 1
    return sequence


def parse_year(filename: str) -> int | None:
    match = re.search(r"(20\d{2})", filename)
    return int(match.group(1)) if match else None


def classify_document(path: Path) -> ClassifiedDocument:
    filename = path.name
    year = parse_year(filename)
    full_text, reader = read_pdf_text(path)
    metadata = reader.metadata or {}
    page_count = len(reader.pages)
    pdf_title = str(metadata.get("/Title", "") or "")
    pdf_author = str(metadata.get("/Author", "") or "")

    if filename.endswith("_Answers.pdf"):
        answer_mode = "text" if len(collapse_inline(full_text)) >= 50 else "ocr"
        return ClassifiedDocument(
            path=path.as_posix(),
            filename=filename,
            family=FAMILY_ANSWERS,
            year=year,
            level="multi-level",
            language="mixed",
            question_count=None,
            is_answer_table=True,
            answer_mode=answer_mode,
            page_count=page_count,
            pdf_title=pdf_title,
            pdf_author=pdf_author,
        )

    sequence = detect_question_sequence(full_text)
    question_count = len(sequence) or None

    if "gr0102e" in filename:
        family = FAMILY_CANADA
        level = "grade-1-2"
        language = "en"
        question_count = 18
    elif filename.endswith("_Felix.pdf"):
        if question_count == 24:
            family = FAMILY_FELIX_BR_24
            level = "level-p"
        elif question_count == 16:
            family = FAMILY_FELIX_AT_16
            level = "felix"
        else:
            family = FAMILY_FELIX_AT_15
            level = "felix"
        language = "en"
    else:
        raise ValueError(f"Unsupported PDF naming pattern: {filename}")

    return ClassifiedDocument(
        path=path.as_posix(),
        filename=filename,
        family=family,
        year=year,
        level=level,
        language=language,
        question_count=question_count,
        is_answer_table=False,
        answer_mode=None,
        page_count=page_count,
        pdf_title=pdf_title,
        pdf_author=pdf_author,
    )


def classify_documents(source_dir: Path | str) -> list[ClassifiedDocument]:
    source_path = Path(source_dir)
    return [classify_document(path) for path in sorted(source_path.glob("*.pdf"))]


def build_exam_id(document: ClassifiedDocument) -> str:
    if document.family == FAMILY_CANADA:
        return f"canada-gr0102e-{document.year}"
    if document.family == FAMILY_FELIX_BR_24:
        return f"felix-brazil-{document.year}"
    if document.family in {FAMILY_FELIX_AT_15, FAMILY_FELIX_AT_16}:
        return f"felix-austria-{document.year}"
    raise ValueError(f"Unsupported exam family for exam id: {document.family}")


def filter_noise_lines(text: str) -> str:
    lines: list[str] = []
    for raw_line in normalize_space(text).splitlines():
        line = collapse_inline(raw_line)
        if not line:
            continue
        if NOISE_LINE_RE.search(line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def extract_duration_minutes(text: str, family: str) -> int | None:
    for pattern in (r"(\d+)\s*minutes", r"(\d+)\s*min\b"):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    if family == FAMILY_CANADA:
        return 45
    return None


def scoring_rules_for_family(family: str, question_count: int) -> list[dict[str, int]]:
    if family == FAMILY_CANADA:
        return [
            {"from": 1, "to": 6, "points": 3},
            {"from": 7, "to": 12, "points": 4},
            {"from": 13, "to": 18, "points": 5},
        ]
    if family == FAMILY_FELIX_BR_24:
        return [
            {"from": 1, "to": 8, "points": 3},
            {"from": 9, "to": 16, "points": 4},
            {"from": 17, "to": 24, "points": 5},
        ]
    if family == FAMILY_FELIX_AT_16:
        return [
            {"from": 1, "to": 5, "points": 3},
            {"from": 6, "to": 10, "points": 4},
            {"from": 11, "to": 16, "points": 5},
        ]
    if family == FAMILY_FELIX_AT_15:
        return [
            {"from": 1, "to": 5, "points": 3},
            {"from": 6, "to": 10, "points": 4},
            {"from": 11, "to": 15, "points": 5},
        ]
    raise ValueError(f"Unsupported family for scoring rules: {family}")


def infer_part(question_number: int, family: str, question_count: int) -> tuple[str, int]:
    rules = scoring_rules_for_family(family, question_count)
    labels = ["part_a", "part_b", "part_c"]
    for label, rule in zip(labels, rules):
        if rule["from"] <= question_number <= rule["to"]:
            return label, rule["points"]
    fallback = rules[-1]
    return labels[-1], fallback["points"]


def question_page_window(document: ClassifiedDocument, doc: fitz.Document) -> tuple[int, int]:
    if document.family == FAMILY_CANADA:
        start_page = 0
        for page_index in range(max(0, len(doc) - 1)):
            page_text = collapse_inline(doc[page_index].get_text("text"))
            if "PART A" in page_text and ("PROBLEMS" in page_text or "Grade 1-2" in page_text):
                start_page = page_index
                break
        end_page = max(start_page + 1, len(doc) - 1)
        return start_page, end_page
    for page_index, page in enumerate(doc):
        page_text = page.get_text("text")
        has_real_question_one = any(
            text == "1." and x0 <= page.rect.width * 0.2 and y0 >= page.rect.height * 0.1
            for x0, y0, _x1, _y1, text, *_ in page.get_text("words")
        )
        if has_real_question_one and "(A)" in page_text:
            return page_index, len(doc)
    return 0, len(doc)


def collect_question_anchors(
    doc: fitz.Document,
    expected_count: int,
    start_page_index: int = 0,
    end_page_index: int | None = None,
) -> list[QuestionAnchor]:
    anchors: list[QuestionAnchor] = []
    started = False
    expected = 1
    end_index = len(doc) if end_page_index is None else min(len(doc), end_page_index)
    for page_index in range(start_page_index, end_index):
        page = doc[page_index]
        words = sorted(page.get_text("words"), key=lambda item: (item[1], item[0]))
        for x0, y0, x1, y1, text, *_ in words:
            match = QUESTION_WORD_RE.match(text)
            if not match:
                continue
            number = int(match.group(1))
            if not started:
                if number != 1:
                    continue
                anchors.append(QuestionAnchor(number=1, page_index=page_index, rect=(x0, y0, x1, y1)))
                started = True
                expected = 2
                if expected_count == 1:
                    return anchors
                continue
            if number != expected:
                continue
            anchors.append(QuestionAnchor(number=number, page_index=page_index, rect=(x0, y0, x1, y1)))
            expected += 1
            if len(anchors) == expected_count:
                return anchors
    return anchors


def build_page_block_cache(doc: fitz.Document) -> dict[int, list[dict[str, Any]]]:
    cache: dict[int, list[dict[str, Any]]] = {}
    for page_index, page in enumerate(doc):
        blocks: list[dict[str, Any]] = []
        for block_index, block in enumerate(page.get_text("blocks")):
            x0, y0, x1, y1, text, *_ = block
            blocks.append(
                {
                    "id": f"p{page_index + 1}_b{block_index}",
                    "rect": fitz.Rect(x0, y0, x1, y1),
                    "text": text,
                }
            )
        cache[page_index] = blocks
    return cache


def collect_image_rects(page: fitz.Page) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    for image in page.get_images(full=True):
        xref = image[0]
        for rect in page.get_image_rects(xref):
            rects.append(rect)
    return rects


def extract_intro_lines(doc: fitz.Document, first_anchor: QuestionAnchor) -> list[str]:
    intro_parts: list[str] = []
    for page_index in range(first_anchor.page_index):
        intro_parts.append(doc[page_index].get_text("text"))
    first_page = doc[first_anchor.page_index]
    top_clip = fitz.Rect(0, 0, first_page.rect.width, max(0.0, first_anchor.rect[1] - 6.0))
    if top_clip.height > 0:
        intro_parts.append(first_page.get_text("text", clip=top_clip))
    intro_text = filter_noise_lines("\n".join(intro_parts))
    return [line for line in intro_text.splitlines() if line]


def question_bbox_for_anchor(doc: fitz.Document, anchor: QuestionAnchor, next_anchor: QuestionAnchor | None) -> fitz.Rect:
    page = doc[anchor.page_index]
    page_rect = page.rect
    y0 = max(0.0, anchor.rect[1] - 6.0)
    if next_anchor and next_anchor.page_index == anchor.page_index:
        y1 = max(y0 + 8.0, next_anchor.rect[1] - 8.0)
    else:
        y1 = max(y0 + 8.0, page_rect.height - 42.0)
    return fitz.Rect(0.0, y0, page_rect.width, min(page_rect.height, y1))


def parse_choices(question_text: str) -> tuple[str, list[dict[str, Any]]]:
    parts = re.split(r"\(([A-E])\)", question_text)
    choice_texts = {label: "" for label in OPTION_LABELS}
    stem_text = collapse_inline(parts[0]) if parts else ""
    if len(parts) > 1:
        for index in range(1, len(parts) - 1, 2):
            label = parts[index]
            choice_texts[label] = collapse_inline(parts[index + 1])
    choices = [{"label": label, "text": choice_texts[label], "asset_refs": []} for label in OPTION_LABELS]
    return stem_text, choices


def option_label_from_token(text: str) -> str | None:
    compact = collapse_inline(text)
    match = OPTION_TOKEN_RE.fullmatch(compact)
    if match:
        return match.group(1)
    if len(compact) == 2 and compact[0] in "([" and compact[1] in OPTION_LABELS:
        return compact[1]
    if len(compact) == 2 and compact[0] in OPTION_LABELS and compact[1] in ")]":
        return compact[0]
    return None


def group_words_into_rows(
    words: list[tuple[float, float, float, float, str, int, int, int]],
    tolerance: float = 4.0,
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


def dedupe_segment_words(
    words: list[tuple[float, float, float, float, str, int, int, int]],
) -> list[str]:
    kept: list[tuple[str, fitz.Rect]] = []
    for x0, y0, x1, y1, text, *_ in sorted(words, key=lambda item: item[0]):
        compact = collapse_inline(text)
        if not compact:
            continue
        rect = fitz.Rect(x0, y0, x1, y1)
        if kept:
            previous_text, previous_rect = kept[-1]
            overlap = max(0.0, min(previous_rect.x1, rect.x1) - max(previous_rect.x0, rect.x0))
            minimum_width = max(1.0, min(previous_rect.width, rect.width))
            if overlap >= minimum_width * 0.35:
                if compact in previous_text:
                    continue
                if previous_text in compact:
                    kept[-1] = (compact, rect)
                    continue
        kept.append((compact, rect))
    return [text for text, _rect in kept]


def normalize_choice_text(text: str) -> str:
    cleaned = collapse_inline(text)
    cleaned = re.sub(r"\bmeter\s*rs\b", "meters", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmet\s*ters\b", "meters", cleaned, flags=re.IGNORECASE)
    return cleaned


def repair_choice_texts_from_words(page: fitz.Page, bbox: fitz.Rect) -> dict[str, str]:
    words = page.get_text("words", clip=bbox)
    rows = group_words_into_rows(words)
    best_row_index = -1
    best_labels: dict[str, tuple[float, float, float, float, str, int, int, int]] = {}

    for row_index, row in enumerate(rows):
        labels: dict[str, tuple[float, float, float, float, str, int, int, int]] = {}
        for word in row:
            label = option_label_from_token(word[4])
            if label and label not in labels:
                labels[label] = word
        if len(labels) > len(best_labels):
            best_labels = labels
            best_row_index = row_index

    if best_row_index < 0 or len(best_labels) < 3:
        return {}

    marker_words = sorted(best_labels.items(), key=lambda item: item[1][0])
    option_texts = {label: "" for label in OPTION_LABELS}
    row = rows[best_row_index]

    for index, (label, marker_word) in enumerate(marker_words):
        start_x = marker_word[2]
        end_x = marker_words[index + 1][1][0] if index + 1 < len(marker_words) else bbox.x1 + 1.0
        segment_words = [
            word
            for word in row
            if word[0] >= start_x - 1.0 and word[2] <= end_x + 1.0 and option_label_from_token(word[4]) is None
        ]
        option_texts[label] = normalize_choice_text(" ".join(dedupe_segment_words(segment_words)))

    last_label = marker_words[-1][0]
    for continuation_row in rows[best_row_index + 1 :]:
        continuation_labels = {option_label_from_token(word[4]) for word in continuation_row if option_label_from_token(word[4])}
        if continuation_labels:
            break
        continuation_tokens = dedupe_segment_words(continuation_row)
        if not continuation_tokens:
            continue
        if len(continuation_tokens) > 3:
            break
        option_texts[last_label] = normalize_choice_text(
            " ".join([option_texts[last_label], *continuation_tokens]).strip()
        )
        break

    if sum(1 for text in option_texts.values() if text) < 3:
        return {}
    return option_texts


def detect_visual_counts(
    page: fitz.Page,
    bbox: fitz.Rect,
    image_rects: list[fitz.Rect],
    drawings: list[Any],
) -> tuple[int, int]:
    image_count = sum(1 for rect in image_rects if rect.intersects(bbox))
    drawing_count = 0
    for drawing in drawings:
        rect = drawing.get("rect") if isinstance(drawing, dict) else drawing
        if rect and rect.intersects(bbox):
            drawing_count += 1
    return image_count, drawing_count


def has_meaningful_visuals(
    image_count: int,
    drawing_count: int,
    choices: list[dict[str, Any]],
) -> bool:
    if image_count > 0 or drawing_count > 0:
        return True
    return any(not choice["text"] for choice in choices)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_clean_dir(path: Path) -> None:
    if path.exists():
        last_error: OSError | None = None
        for attempt in range(4):
            try:
                shutil.rmtree(path)
                break
            except OSError as exc:
                last_error = exc
                time.sleep(0.05 * (attempt + 1))
        else:
            if last_error is not None:
                raise last_error
    path.mkdir(parents=True, exist_ok=True)


def export_reference_crop(page: fitz.Page, bbox: fitz.Rect, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), clip=bbox, alpha=False)
    pixmap.save(output_path.as_posix())


def export_svg_clip(page: fitz.Page, bbox: fitz.Rect) -> str:
    original_crop = fitz.Rect(page.cropbox)
    page.set_cropbox(bbox)
    try:
        return page.get_svg_image(text_as_path=1)
    finally:
        page.set_cropbox(original_crop)


def export_question_asset(
    page: fitz.Page,
    bbox: fitz.Rect,
    asset_id: str,
    assets_dir: Path,
    prefer_svg: bool,
) -> dict[str, Any]:
    if prefer_svg:
        asset_path = assets_dir / f"{asset_id}.svg"
        asset_path.write_text(export_svg_clip(page, bbox), encoding="utf-8")
        asset_format = "svg"
    else:
        asset_path = assets_dir / f"{asset_id}.png"
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=bbox, alpha=False)
        pixmap.save(asset_path.as_posix())
        asset_format = "png"
    return {
        "id": asset_id,
        "path": asset_path.relative_to(assets_dir.parent).as_posix(),
        "kind": "question_region",
        "format": asset_format,
        "page": page.number + 1,
        "bbox": round_rect(bbox),
        "role": "question_crop",
    }


def extract_row_words(page: fitz.Page, question_count: int) -> dict[int, dict[str, tuple[float, float, float, float]]]:
    words = sorted(page.get_text("words"), key=lambda item: (item[1], item[0]))
    rows: dict[int, dict[str, tuple[float, float, float, float]]] = {}
    row_buckets: list[list[tuple[float, float, float, float, str]]] = []

    for x0, y0, x1, y1, text, *_ in words:
        if row_buckets and abs(row_buckets[-1][0][1] - y0) <= 2.5:
            row_buckets[-1].append((x0, y0, x1, y1, text))
        else:
            row_buckets.append([(x0, y0, x1, y1, text)])

    for row in row_buckets:
        numeric_words = [
            item for item in row if item[4].isdigit() and 1 <= int(item[4]) <= question_count
        ]
        if not numeric_words:
            continue
        numeric_words = sorted(numeric_words, key=lambda item: item[0])
        for index, (x0, y0, x1, y1, text) in enumerate(numeric_words):
            number = int(text)
            next_numeric_x = numeric_words[index + 1][0] if index + 1 < len(numeric_words) else float("inf")
            candidates = {
                option_text: (wx0, wy0, wx1, wy1)
                for wx0, wy0, wx1, wy1, option_text in row
                if option_text in OPTION_LABELS and x1 < wx0 < next_numeric_x
            }
            if len(candidates) == 5 and number not in rows:
                rows[number] = candidates
    return rows


def underline_score_from_drawings(
    drawings: list[dict[str, Any]],
    option_bbox: tuple[float, float, float, float],
) -> float:
    x0, y0, x1, y1 = option_bbox
    search = fitz.Rect(x0 - 1.0, y0, x1 + 1.0, y1 + 5.0)
    best = 0.0
    minimum_width = max(6.0, (x1 - x0) * 0.7)
    for drawing in drawings:
        rect = drawing.get("rect")
        if rect is None or not search.intersects(rect):
            continue
        if rect.width < minimum_width or rect.height > 3.0:
            continue
        if drawing.get("type") not in {"s", "f"}:
            continue
        best = max(best, rect.width)
    return best


def underline_score_from_pixels(page: fitz.Page, option_bbox: tuple[float, float, float, float]) -> float:
    x0, y0, x1, y1 = option_bbox
    clip = fitz.Rect(x0 - 2.0, y0 - 1.0, x1 + 2.0, y1 + 5.0)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(6, 6), clip=clip, alpha=False)
    samples = list(pixmap.samples)
    width = pixmap.width
    height = pixmap.height
    channels = pixmap.n
    rows: list[float] = []
    for row_index in range(height):
        start = row_index * width * channels
        end = start + (width * channels)
        row_bytes = samples[start:end]
        row_darkness = 0.0
        for offset in range(0, len(row_bytes), channels):
            r = row_bytes[offset]
            g = row_bytes[offset + 1]
            b = row_bytes[offset + 2]
            row_darkness += 255.0 - ((r + g + b) / 3.0)
        rows.append(row_darkness / width)
    tail = rows[max(0, int(height * 0.6)) :]
    head = rows[: max(1, int(height * 0.4))]
    if not tail or not head:
        return 0.0
    return max(tail) - (sum(head) / len(head))


def extract_canada_answers(doc: fitz.Document, question_count: int) -> dict[str, Any]:
    page = doc[-1]
    drawings = page.get_drawings()
    row_words = extract_row_words(page, question_count)
    answers: dict[str, str] = {}
    confidences: dict[str, float] = {}
    warnings: list[str] = []

    for number in range(1, question_count + 1):
        candidates = row_words.get(number)
        if not candidates:
            warnings.append(f"Missing answer row for question {number} on embedded Canada answer page.")
            continue
        drawing_scores = {
            label: underline_score_from_drawings(drawings, candidates[label]) for label in OPTION_LABELS
        }
        if any(score > 0.0 for score in drawing_scores.values()):
            scores = drawing_scores
        else:
            scores = {
                label: underline_score_from_pixels(page, candidates[label]) for label in OPTION_LABELS
            }
        selected = max(scores, key=scores.get)
        ranked = sorted(scores.values(), reverse=True)
        top = ranked[0]
        second = ranked[1] if len(ranked) > 1 else 0.0
        if top <= 0.0:
            warnings.append(f"Unable to detect embedded answer underline for question {number}.")
            continue
        answers[str(number)] = selected
        confidences[str(number)] = round(min(1.0, top / max(1.0, top + second)), 3)
    return {
        "answers": answers,
        "method": "embedded_answer_page_underline",
        "confidence_by_question": confidences,
        "warnings": warnings,
        "raw_excerpt": collapse_inline(page.get_text("text")[:500]),
    }


def run_tesseract_ocr(path: Path) -> str:
    command = ["tesseract", path.as_posix(), "stdout", "--psm", "6"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def parsed_question_text_score(stem_text: str, choices: list[dict[str, Any]]) -> int:
    stem_words = re.findall(r"[A-Za-z]{3,}", stem_text)
    choice_words = sum(len(re.findall(r"[A-Za-z0-9]{1,}", choice["text"])) for choice in choices)
    filled_choices = sum(1 for choice in choices if choice["text"])
    return (len(stem_words) * 4) + choice_words + (filled_choices * 6)


def should_try_question_ocr(cleaned_text: str, stem_text: str) -> bool:
    if len(collapse_inline(cleaned_text)) < 40:
        return False
    return len(re.findall(r"[A-Za-z]{3,}", stem_text)) < 5


def extract_question_text_ocr(page: fitz.Page, bbox: fitz.Rect) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), clip=bbox, alpha=False).save(temp_path.as_posix())
        return run_tesseract_ocr(temp_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def extract_answer_table_text(answer_document: ClassifiedDocument) -> str:
    path = Path(answer_document.path)
    if answer_document.answer_mode == "text":
        text, _ = read_pdf_text(path)
        return text
    doc = fitz.open(path.as_posix())
    page = doc[0]
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(temp_path.as_posix())
        return run_tesseract_ocr(temp_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def extract_felix_answers(answer_document: ClassifiedDocument, question_count: int) -> dict[str, Any]:
    raw_text = extract_answer_table_text(answer_document)
    lines = [collapse_inline(line) for line in raw_text.splitlines() if collapse_inline(line)]
    preferred_patterns = [
        re.compile(r"^felix2\b", re.IGNORECASE),
        re.compile(r"^felix\b", re.IGNORECASE),
        re.compile(r"\bfelix\b", re.IGNORECASE),
    ]
    felix_line_index = None
    for pattern in preferred_patterns:
        felix_line_index = next((index for index, line in enumerate(lines) if pattern.search(line)), None)
        if felix_line_index is not None:
            break
    warnings: list[str] = []
    if felix_line_index is None:
        warnings.append(f"Could not find Felix answer row in {answer_document.filename}.")
        return {
            "answers": {},
            "method": f"answer_table_{answer_document.answer_mode}",
            "confidence_by_question": {},
            "warnings": warnings,
            "raw_excerpt": collapse_inline(raw_text[:500]),
        }

    felix_chunks = [lines[felix_line_index]]
    for next_line in lines[felix_line_index + 1 :]:
        if LEVEL_ROW_BREAK_RE.match(next_line):
            break
        felix_chunks.append(next_line)
        if len(re.findall(r"[A-E]", " ".join(felix_chunks).upper())) >= question_count:
            break

    letters = re.findall(r"[A-E]", " ".join(felix_chunks).upper())
    if len(letters) < question_count:
        warnings.append(
            f"Expected {question_count} Felix answers in {answer_document.filename}, extracted only {len(letters)} letters."
        )

    answers = {str(index + 1): letter for index, letter in enumerate(letters[:question_count])}
    confidences = {question: 0.9 if answer_document.answer_mode == "text" else 0.75 for question in answers}
    return {
        "answers": answers,
        "method": f"answer_table_{answer_document.answer_mode}",
        "confidence_by_question": confidences,
        "warnings": warnings,
        "raw_excerpt": collapse_inline(" ".join(felix_chunks)[:500]),
    }


def extract_answers(
    document: ClassifiedDocument,
    doc: fitz.Document,
    answer_document: ClassifiedDocument | None,
) -> dict[str, Any]:
    if not document.question_count:
        raise ValueError(f"Document {document.filename} is missing question_count.")
    if document.family == FAMILY_CANADA:
        return extract_canada_answers(doc, document.question_count)
    if answer_document is None:
        return {
            "answers": {},
            "method": "missing_answer_table",
            "confidence_by_question": {},
            "warnings": [f"No answer table found for {document.filename}."],
            "raw_excerpt": "",
        }
    return extract_felix_answers(answer_document, document.question_count)


def extract_questions(
    document: ClassifiedDocument,
    doc: fitz.Document,
    answer_payload: dict[str, Any],
    assets_dir: Path,
    qa_exam_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    if not document.question_count:
        raise ValueError(f"Document {document.filename} is missing question_count.")

    warnings: list[str] = []
    start_page_index, end_page_index = question_page_window(document, doc)
    anchors = collect_question_anchors(doc, document.question_count, start_page_index, end_page_index)
    if len(anchors) != document.question_count:
        warnings.append(
            f"Expected {document.question_count} question anchors in {document.filename}, found {len(anchors)}."
        )

    block_cache = build_page_block_cache(doc)
    word_cache = build_page_word_cache(doc)
    visual_cache = build_page_visual_cache(doc)
    assets: list[dict[str, Any]] = []
    audit_questions: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []

    for index, anchor in enumerate(anchors):
        previous_anchor = anchors[index - 1] if index > 0 else None
        next_anchor = anchors[index + 1] if index + 1 < len(anchors) else None
        page = doc[anchor.page_index]
        text_bbox = question_bbox_for_anchor(doc, anchor, next_anchor)
        raw_question_text = page.get_text("text", clip=text_bbox)
        cleaned_text = filter_noise_lines(raw_question_text)
        cleaned_text = re.sub(rf"^\s*{anchor.number}\.\s*", "", cleaned_text, count=1)
        stem_text, choices = parse_choices(cleaned_text)
        repaired_choice_texts = repair_choice_texts_from_words(page, text_bbox)
        if repaired_choice_texts:
            for choice in choices:
                repaired_text = repaired_choice_texts.get(choice["label"], "")
                if repaired_text:
                    choice["text"] = repaired_text
        if should_try_question_ocr(cleaned_text, stem_text):
            ocr_text = filter_noise_lines(extract_question_text_ocr(page, text_bbox))
            ocr_text = re.sub(rf"^\s*{anchor.number}\.\s*", "", ocr_text, count=1)
            ocr_stem_text, ocr_choices = parse_choices(ocr_text)
            ocr_choice_repairs = repair_choice_texts_from_words(page, text_bbox)
            if ocr_choice_repairs:
                for choice in ocr_choices:
                    repaired_text = ocr_choice_repairs.get(choice["label"], "")
                    if repaired_text:
                        choice["text"] = repaired_text
            if parsed_question_text_score(ocr_stem_text, ocr_choices) > parsed_question_text_score(stem_text, choices):
                cleaned_text = ocr_text
                stem_text = ocr_stem_text
                choices = ocr_choices

        asset_payload = extract_question_assets(
            document_family=document.family,
            page=page,
            question_number=anchor.number,
            question_bbox=text_bbox,
            previous_anchor=previous_anchor,
            page_words=word_cache[anchor.page_index],
            page_visuals=visual_cache[anchor.page_index],
            choices=choices,
            assets_dir=assets_dir,
            year=document.year,
        )
        shared_asset_refs = list(asset_payload["shared_asset_refs"])
        for choice in choices:
            choice["asset_refs"] = list(asset_payload["option_asset_refs"].get(choice["label"], []))
        assets.extend(asset_payload["assets"])
        reference_bbox = fitz.Rect(asset_payload["reference_bbox"])
        reference_rel_path = Path("images") / f"q{anchor.number:02d}_reference.png"
        export_reference_crop(page, reference_bbox, qa_exam_dir / reference_rel_path)

        question_block_ids = [
            block["id"]
            for block in block_cache[anchor.page_index]
            if block["rect"].intersects(reference_bbox) and not NOISE_LINE_RE.search(collapse_inline(block["text"]))
        ]
        part, points = infer_part(anchor.number, document.family, document.question_count)
        answer = answer_payload["answers"].get(str(anchor.number))
        answer_confidence = float(answer_payload["confidence_by_question"].get(str(anchor.number), 0.0))
        missing_option_assets = [
            choice["label"]
            for choice in choices
            if choice_requires_asset(choice["text"]) and not choice["asset_refs"]
        ]
        any_required_option_assets = any(choice_requires_asset(choice["text"]) for choice in choices)
        has_assets = bool(shared_asset_refs or any(choice["asset_refs"] for choice in choices))
        option_asset_count = sum(1 for choice in choices if choice["asset_refs"])
        visual_count = asset_payload["visual_counts"]["images"] + asset_payload["visual_counts"]["drawings"]
        needs_review = bool(
            not stem_text
            or answer is None
            or len(choices) != 5
            or (missing_option_assets and option_asset_count >= 2)
            or (visual_count > 0 and not has_assets and any_required_option_assets)
        )
        confidence = round(
            max(
                0.0,
                min(
                    1.0,
                    (0.55 if stem_text else 0.0)
                    + (0.2 if len(choices) == 5 else 0.0)
                    + (0.25 if answer else 0.0)
                    + (0.15 if has_assets or visual_count == 0 else 0.0)
                    + (0.1 * answer_confidence),
                ),
            ),
            3,
        )
        source = {
            "page": anchor.page_index + 1,
            "bbox": asset_payload["reference_bbox"],
            "block_ids": question_block_ids,
            "answer_source": answer_payload["method"],
            "confidence": confidence,
            "needs_review": needs_review,
        }
        question_payload = {
            "id": f"q{anchor.number:02d}",
            "number": anchor.number,
            "part": part,
            "points": points,
            "stem_text": stem_text,
            "choices": choices,
            "shared_asset_refs": shared_asset_refs,
            "answer": answer,
            "source": source,
        }
        questions.append(question_payload)
        audit_questions.append(
            {
                "number": anchor.number,
                "page": anchor.page_index + 1,
                "text_bbox": round_rect(text_bbox),
                "reference_bbox": asset_payload["reference_bbox"],
                "block_ids": question_block_ids,
                "raw_text": cleaned_text,
                "visual_counts": asset_payload["visual_counts"],
                "qa_reference_path": reference_rel_path.as_posix(),
                "asset_assignments": asset_payload["assignment_audit"],
                "exported_assets": {
                    "stem": shared_asset_refs,
                    "options": {choice["label"]: choice["asset_refs"] for choice in choices if choice["asset_refs"]},
                },
                "answer": answer,
                "answer_confidence": answer_confidence,
                "missing_option_assets": missing_option_assets,
                "needs_review": needs_review,
            }
        )

    return questions, assets, audit_questions, warnings


def extract_exam(
    document: ClassifiedDocument,
    answer_document: ClassifiedDocument | None,
    output_root: Path,
    qa_root: Path,
) -> dict[str, Any]:
    exam_id = build_exam_id(document)
    doc = fitz.open(document.path)
    exam_dir = output_root / "exams" / exam_id
    assets_dir = exam_dir / "assets"
    qa_exam_dir = qa_root / exam_id
    prepare_clean_dir(assets_dir)
    prepare_clean_dir(qa_exam_dir)

    start_page_index, end_page_index = question_page_window(document, doc)
    anchors = collect_question_anchors(doc, document.question_count or 0, start_page_index, end_page_index)
    if not anchors:
        raise ValueError(f"Could not find any question anchors in {document.filename}.")

    intro_lines = extract_intro_lines(doc, anchors[0])
    duration_minutes = extract_duration_minutes("\n".join(intro_lines), document.family)
    scoring_rules = scoring_rules_for_family(document.family, document.question_count or len(anchors))
    answer_payload = extract_answers(document, doc, answer_document)
    questions, assets, audit_questions, extraction_warnings = extract_questions(
        document,
        doc,
        answer_payload,
        assets_dir,
        qa_exam_dir,
    )
    warnings = [*answer_payload["warnings"], *extraction_warnings]
    answer_key = {str(question["number"]): question["answer"] for question in questions if question["answer"]}
    exam_json = {
        "exam_id": exam_id,
        "year": document.year,
        "family": document.family,
        "level": document.level,
        "language": document.language,
        "source_pdf": document.path,
        "duration_minutes": duration_minutes,
        "question_count": document.question_count,
        "scoring_rules": scoring_rules,
        "instructions": intro_lines,
        "assets": assets,
        "questions": questions,
        "answer_key": answer_key,
        "source_audit_ref": f"exams/{exam_id}/audit.json",
        "warnings": warnings,
    }
    audit_json = {
        "exam_id": exam_id,
        "source_document": asdict(document),
        "answer_source": {
            "document": answer_document.path if answer_document else document.path,
            "method": answer_payload["method"],
            "raw_excerpt": answer_payload["raw_excerpt"],
            "warnings": answer_payload["warnings"],
        },
        "question_count_expected": document.question_count,
        "question_count_extracted": len(questions),
        "warnings": warnings,
        "questions": audit_questions,
        "assets": assets,
    }
    write_json(exam_dir / "exam.json", exam_json)
    write_json(exam_dir / "audit.json", audit_json)
    qa_page_path = build_asset_qa_page(exam_dir, qa_exam_dir, exam_json, audit_json)
    audit_json["qa_review_ref"] = qa_page_path.as_posix()
    write_json(exam_dir / "audit.json", audit_json)
    return {
        "exam_id": exam_id,
        "output_dir": exam_dir.as_posix(),
        "qa_review_ref": qa_page_path.as_posix(),
        "family": document.family,
        "year": document.year,
        "question_count": document.question_count,
        "answer_count": len(answer_key),
        "warnings": warnings,
    }


def build_dataset(source_dir: Path | str, output_dir: Path | str) -> dict[str, Any]:
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    qa_root = output_path.parent / "reports" / "asset-qa"
    documents = classify_documents(source_path)
    answer_documents = {document.year: document for document in documents if document.is_answer_table}
    output_path.mkdir(parents=True, exist_ok=True)
    prepare_clean_dir(qa_root)

    exams: list[dict[str, Any]] = []
    for document in documents:
        if document.is_answer_table:
            continue
        exams.append(extract_exam(document, answer_documents.get(document.year), output_path, qa_root))

    qa_index_path = build_asset_qa_index(qa_root, exams)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": source_path.as_posix(),
        "output_root": output_path.as_posix(),
        "qa_output_root": qa_root.as_posix(),
        "qa_index_ref": qa_index_path.as_posix(),
        "source_documents": [asdict(document) for document in documents],
        "exams": exams,
    }
    write_json(output_path / "manifest.json", manifest)
    return manifest
