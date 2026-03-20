from __future__ import annotations

import html
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

try:
    import pdfplumber
except ModuleNotFoundError:  # pragma: no cover - optional dependency in local envs
    pdfplumber = None

from .pipeline import (
    NOISE_LINE_RE,
    OPTION_LABELS,
    classify_documents,
    classify_document,
    collapse_inline,
    collect_question_anchors,
    extract_answers,
    group_words_into_rows,
    option_label_from_token,
    parse_choices,
    question_page_window,
    question_bbox_for_anchor,
    round_rect,
    run_tesseract_ocr,
)

SCHEMA_VERSION = 2
MANIFEST_KEYS = {
    "schema_version",
    "generated_at",
    "source_dir",
    "data_dir",
    "output_dir",
    "report_dir",
    "engine_status",
    "field_count",
    "exams",
}
MANIFEST_EXAM_KEYS = {
    "exam_id",
    "source_pdf",
    "question_count",
    "field_count",
    "changed_count",
    "suspicious_count",
    "unchanged_count",
    "image_only_count",
    "path",
    "report_path",
}
REVIEW_FILE_KEYS = {
    "schema_version",
    "generated_at",
    "exam_id",
    "source_pdf",
    "question_count",
    "field_count",
    "fields",
}
FIELD_KEYS = {
    "field_id",
    "question_number",
    "kind",
    "choice_label",
    "expected_mode",
    "baseline_text",
    "extracted_text",
    "verified_text",
    "status",
    "review_priority",
    "method",
    "confidence",
    "page",
    "text_bbox",
    "asset_refs",
    "review_status",
    "review_notes",
    "reviewed_at",
}

SECTION_BREAK_RE = re.compile(
    r"^(?:PART\s+[ABC]\b.*|[\-\u2013\u2014 ]*\d+\s*Point Questions?[\-\u2013\u2014 ]*)$",
    re.IGNORECASE,
)
TRAILING_OPTION_NOISE_RE = re.compile(r"^(?:[A-Za-z0-9]\s*){1,8}$")
SPACED_SINGLE_CHAR_RE = re.compile(r"^(?:[A-Za-z0-9]\s+){2,}[A-Za-z0-9]$")
TEXT_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
LETTER_WORD_RE = re.compile(r"[A-Za-z]{3,}")
SUSPICIOUS_PATTERNS = (
    re.compile(r"\b(?:copyright|all rights reserved|do not duplicate|written permission)\b", re.IGNORECASE),
    re.compile(r"\bPART\s+[ABC]\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*Point Questions?\b", re.IGNORECASE),
)
TESSERACT_PRESENT = shutil.which("tesseract") is not None
REVIEW_STATUS_VALUES = {"pending", "approved", "needs_review", "not_applicable"}


class TextReviewValidationError(ValueError):
    pass


def build_text_review_dataset(
    source_dir: Path | str,
    data_dir: Path | str,
    output_dir: Path | str,
    report_dir: Path | str,
    *,
    exam_ids: list[str] | None = None,
) -> dict[str, Any]:
    source_path = Path(source_dir).resolve()
    data_path = Path(data_dir).resolve()
    output_path = Path(output_dir).resolve()
    report_path = Path(report_dir).resolve()

    output_path.mkdir(parents=True, exist_ok=True)
    report_path.mkdir(parents=True, exist_ok=True)

    data_manifest = _read_json(data_path / "manifest.json")
    selected_exam_ids = _select_exam_ids(data_manifest, exam_ids)
    source_documents = classify_documents(source_path)
    answer_documents_by_year = {document.year: document for document in source_documents if document.is_answer_table}
    manifest_exams: list[dict[str, Any]] = []
    total_field_count = 0

    for exam_id in selected_exam_ids:
        exam_payload = _read_json(data_path / "exams" / exam_id / "exam.json")
        exam_result = _build_exam_review(
            exam_payload=exam_payload,
            source_path=source_path,
            output_path=output_path,
            report_path=report_path,
            answer_documents_by_year=answer_documents_by_year,
        )
        manifest_exams.append(exam_result["manifest_entry"])
        total_field_count += exam_result["manifest_entry"]["field_count"]

    index_path = report_path / "index.html"
    index_path.write_text(
        _index_report_html(
            manifest_exams=manifest_exams,
            generated_at=datetime.now(timezone.utc),
        ),
        encoding="utf-8",
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": source_path.as_posix(),
        "data_dir": data_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "report_dir": report_path.as_posix(),
        "engine_status": {
            "pymupdf": True,
            "pdfplumber": pdfplumber is not None,
            "tesseract": TESSERACT_PRESENT,
        },
        "field_count": total_field_count,
        "exams": manifest_exams,
    }
    _write_json(output_path / "manifest.json", manifest)
    return manifest


def validate_text_review_dataset(
    output_dir: Path | str,
    report_dir: Path | str,
    *,
    exam_ids: list[str] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    report_path = Path(report_dir).resolve()
    manifest = _read_json(output_path / "manifest.json")

    _validate_exact_keys(manifest, MANIFEST_KEYS, "text review manifest")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise TextReviewValidationError(
            f"text review manifest schema_version must be {SCHEMA_VERSION}, got {manifest.get('schema_version')!r}"
        )

    selected_exam_ids = set(exam_ids or [])
    entries = [
        entry for entry in manifest["exams"] if not selected_exam_ids or entry.get("exam_id") in selected_exam_ids
    ]
    if selected_exam_ids:
        known = {entry["exam_id"] for entry in manifest["exams"]}
        missing = sorted(selected_exam_ids - known)
        if missing:
            raise TextReviewValidationError(f"Unknown exam_id values in validation: {', '.join(missing)}")

    total_fields = 0
    for entry in entries:
        _validate_exact_keys(entry, MANIFEST_EXAM_KEYS, f"manifest entry {entry.get('exam_id')}")
        review_file = output_path / Path(entry["path"]).name
        if not review_file.exists():
            raise TextReviewValidationError(f"Missing review JSON for {entry['exam_id']}: {review_file}")
        report_file = report_path / Path(entry["report_path"]).name
        if not report_file.exists():
            raise TextReviewValidationError(f"Missing report HTML for {entry['exam_id']}: {report_file}")

        payload = _read_json(review_file)
        _validate_exact_keys(payload, REVIEW_FILE_KEYS, review_file.name)
        if payload["exam_id"] != entry["exam_id"]:
            raise TextReviewValidationError(
                f"Review file exam_id mismatch for {review_file.name}: {payload['exam_id']!r} != {entry['exam_id']!r}"
            )
        if payload["field_count"] != len(payload["fields"]):
            raise TextReviewValidationError(f"Review file {review_file.name} field_count does not match fields length")
        total_fields += len(payload["fields"])
        for field in payload["fields"]:
            _validate_exact_keys(field, FIELD_KEYS, f"{review_file.name} field {field.get('field_id')}")

    index_path = report_path / "index.html"
    if not index_path.exists():
        raise TextReviewValidationError(f"Missing index report: {index_path}")

    return {
        "output_dir": output_path.as_posix(),
        "report_dir": report_path.as_posix(),
        "exam_count": len(entries),
        "field_count": total_fields,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_exam_review(
    *,
    exam_payload: dict[str, Any],
    source_path: Path,
    output_path: Path,
    report_path: Path,
    answer_documents_by_year: dict[int | None, Any],
) -> dict[str, Any]:
    exam_id = exam_payload["exam_id"]
    source_pdf = Path(exam_payload["source_pdf"])
    if not source_pdf.is_absolute():
        source_pdf = (source_path / source_pdf).resolve()
    if not source_pdf.exists():
        raise FileNotFoundError(f"Missing source PDF for {exam_id}: {source_pdf}")

    document = classify_document(source_pdf)
    answer_document = answer_documents_by_year.get(document.year)
    fitz_doc = fitz.open(source_pdf.as_posix())
    plumber_doc = pdfplumber.open(source_pdf.as_posix()) if pdfplumber is not None else None
    try:
        start_page_index, end_page_index = question_page_window(document, fitz_doc)
        anchors = collect_question_anchors(
            fitz_doc,
            len(exam_payload["questions"]),
            start_page_index,
            end_page_index,
        )
        anchor_by_number = {anchor.number: anchor for anchor in anchors}
        answer_payload = extract_answers(document, fitz_doc, answer_document)

        fields: list[dict[str, Any]] = []
        counts = {"changed": 0, "suspicious": 0, "unchanged": 0, "image_only": 0}
        for index, question in enumerate(exam_payload["questions"]):
            question_number = int(question["number"])
            anchor = anchor_by_number.get(question_number)
            if anchor is None:
                raise TextReviewValidationError(f"Could not find anchor for {exam_id} question {question_number}")
            next_anchor = anchors[index + 1] if index + 1 < len(anchors) else None
            extracted = _extract_question_candidates(
                fitz_doc=fitz_doc,
                plumber_doc=plumber_doc,
                anchor=anchor,
                next_anchor=next_anchor,
                question_number=question_number,
            )
            question_fields = _build_question_fields(question, extracted, answer_payload)
            for field in question_fields:
                counts[field["review_priority"]] += 1
                fields.append(field)
    finally:
        fitz_doc.close()
        if plumber_doc is not None:
            plumber_doc.close()

    review_path = output_path / f"{exam_id}.json"
    existing_fields = _load_existing_field_state(review_path)
    fields = [_merge_existing_review_state(field, existing_fields.get(field["field_id"])) for field in fields]

    review_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exam_id": exam_id,
        "source_pdf": source_pdf.as_posix(),
        "question_count": len(exam_payload["questions"]),
        "field_count": len(fields),
        "fields": fields,
    }
    _write_json(review_path, review_payload)

    report_file = report_path / f"{exam_id}.html"
    report_file.write_text(
        _exam_report_html(review_payload),
        encoding="utf-8",
    )

    return {
        "manifest_entry": {
            "exam_id": exam_id,
            "source_pdf": source_pdf.as_posix(),
            "question_count": len(exam_payload["questions"]),
            "field_count": len(fields),
            "changed_count": counts["changed"],
            "suspicious_count": counts["suspicious"],
            "unchanged_count": counts["unchanged"],
            "image_only_count": counts["image_only"],
            "path": review_path.name,
            "report_path": report_file.name,
        }
    }


def _build_question_fields(
    question: dict[str, Any],
    extracted: dict[str, Any],
    answer_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    page_number = extracted["page"]
    stem_asset_refs = list(question.get("shared_asset_refs", []))
    question_choice_asset_count = sum(1 for choice in question.get("choices", []) if choice.get("asset_refs"))
    stem_mode = _classify_expected_mode(
        kind="stem",
        baseline_text=question.get("stem_text", ""),
        asset_refs=stem_asset_refs,
    )
    stem_text = _clean_field_text(
        extracted["stem_text"],
        expected_mode=stem_mode,
        asset_refs=stem_asset_refs,
    )
    stem_suspicious = _is_field_suspicious(stem_text, expected_mode=stem_mode, asset_refs=stem_asset_refs)
    stem_method = _finalize_method(extracted["methods"]["stem"], stem_suspicious)
    fields = [
        _build_field_record(
            field_id=f"q{question['number']:02d}.stem",
            question_number=question["number"],
            kind="stem",
            choice_label=None,
            expected_mode=stem_mode,
            baseline_text=question.get("stem_text", ""),
            extracted_text=stem_text,
            method=stem_method,
            confidence=_field_confidence(stem_method, stem_text, stem_suspicious),
            page=page_number,
            text_bbox=extracted["field_bboxes"]["stem"],
            asset_refs=stem_asset_refs,
        )
    ]

    baseline_choices = {choice["label"]: choice for choice in question.get("choices", [])}
    for label in OPTION_LABELS:
        choice = baseline_choices[label]
        asset_refs = list(choice.get("asset_refs", []))
        extracted_choice_text = extracted["choices"].get(label, "")
        expected_mode = _classify_expected_mode(
            kind="choice",
            baseline_text=choice.get("text", ""),
            asset_refs=asset_refs,
        )
        if (
            expected_mode == "text_required"
            and not asset_refs
            and question_choice_asset_count >= 3
            and (
                _looks_like_visual_sequence(choice.get("text", ""))
                or _looks_like_visual_sequence(extracted_choice_text)
            )
        ):
            expected_mode = "image_only"
        extracted_text = _clean_field_text(
            extracted_choice_text,
            expected_mode=expected_mode,
            asset_refs=asset_refs,
        )
        method = extracted["methods"]["choices"].get(label, extracted["question_method"])
        suspicious = _is_field_suspicious(
            extracted_text,
            expected_mode=expected_mode,
            asset_refs=asset_refs,
        )
        if (
            suspicious
            and expected_mode != "image_only"
            and not asset_refs
            and extracted["choice_bboxes"].get(label) != extracted["question_bbox"]
        ):
            ocr_text = _ocr_choice_snippet(
                page=extracted["fitz_page"],
                bbox=fitz.Rect(extracted["choice_bboxes"][label]),
                baseline_text=choice.get("text", ""),
            )
            ocr_text = _clean_field_text(
                ocr_text,
                expected_mode=expected_mode,
                asset_refs=asset_refs,
            )
            if _candidate_score(ocr_text, expected_mode=expected_mode, asset_refs=asset_refs) > _candidate_score(
                extracted_text,
                expected_mode=expected_mode,
                asset_refs=asset_refs,
            ):
                extracted_text = ocr_text
                method = "tesseract_snippet"
                suspicious = _is_field_suspicious(
                    extracted_text,
                    expected_mode=expected_mode,
                    asset_refs=asset_refs,
                )

        fields.append(
            _build_field_record(
                field_id=f"q{question['number']:02d}.choice.{label}",
                question_number=question["number"],
                kind="choice",
                choice_label=label,
                expected_mode=expected_mode,
                baseline_text=choice.get("text", ""),
                extracted_text=extracted_text,
                method=_finalize_method(method, suspicious),
                confidence=_field_confidence(method, extracted_text, suspicious),
                page=page_number,
                text_bbox=extracted["choice_bboxes"][label],
                asset_refs=asset_refs,
            )
        )

    answer_text = collapse_inline(answer_payload["answers"].get(str(question["number"]), ""))
    answer_confidence = float(answer_payload["confidence_by_question"].get(str(question["number"]), 0.0))
    answer_method = answer_payload["method"]
    answer_page = int(answer_payload.get("page_by_question", {}).get(str(question["number"]), page_number))
    answer_bbox = list(answer_payload.get("bbox_by_question", {}).get(str(question["number"]), []))
    fields.append(
        _build_field_record(
            field_id=f"q{question['number']:02d}.answer",
            question_number=question["number"],
            kind="answer",
            choice_label=None,
            expected_mode="text_required",
            baseline_text=question.get("answer", "") or "",
            extracted_text=answer_text,
            method=_finalize_method(
                answer_method,
                _is_field_suspicious(answer_text, expected_mode="text_required", asset_refs=[]),
            ),
            confidence=answer_confidence or _field_confidence(
                answer_method,
                answer_text,
                _is_field_suspicious(answer_text, expected_mode="text_required", asset_refs=[]),
            ),
            page=answer_page,
            text_bbox=answer_bbox,
            asset_refs=[],
        )
    )

    return fields


def _build_field_record(
    *,
    field_id: str,
    question_number: int,
    kind: str,
    choice_label: str | None,
    expected_mode: str,
    baseline_text: str,
    extracted_text: str,
    method: str,
    confidence: float,
    page: int,
    text_bbox: list[float],
    asset_refs: list[str],
) -> dict[str, Any]:
    suspicious = _is_field_suspicious(extracted_text, expected_mode=expected_mode, asset_refs=asset_refs)
    status = "image_only" if expected_mode == "image_only" else "pending"
    review_priority = _review_priority(
        baseline_text=baseline_text,
        extracted_text=extracted_text,
        expected_mode=expected_mode,
        suspicious=suspicious,
    )
    return {
        "field_id": field_id,
        "question_number": question_number,
        "kind": kind,
        "choice_label": choice_label,
        "expected_mode": expected_mode,
        "baseline_text": baseline_text,
        "extracted_text": extracted_text,
        "verified_text": "",
        "status": status,
        "review_priority": review_priority,
        "method": method,
        "confidence": round(confidence, 3),
        "page": int(page),
        "text_bbox": [round(float(value), 2) for value in text_bbox],
        "asset_refs": asset_refs,
        "review_status": "not_applicable" if status == "image_only" else "pending",
        "review_notes": "",
        "reviewed_at": None,
    }


def _load_existing_field_state(review_path: Path) -> dict[str, dict[str, Any]]:
    if not review_path.exists():
        return {}
    payload = _read_json(review_path)
    fields = payload.get("fields", [])
    if not isinstance(fields, list):
        return {}
    existing: dict[str, dict[str, Any]] = {}
    for field in fields:
        field_id = field.get("field_id")
        if isinstance(field_id, str):
            existing[field_id] = field
    return existing


def _merge_existing_review_state(field: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    if not existing:
        return field

    merged = dict(field)
    merged["verified_text"] = str(existing.get("verified_text", merged["verified_text"]) or "")

    review_status = existing.get("review_status")
    if review_status not in REVIEW_STATUS_VALUES:
        review_status = _default_review_status(field["status"])
    merged["review_status"] = review_status
    merged["review_notes"] = str(existing.get("review_notes", "") or "")
    reviewed_at = existing.get("reviewed_at")
    merged["reviewed_at"] = reviewed_at if isinstance(reviewed_at, str) or reviewed_at is None else None
    return merged


def _default_review_status(status: str) -> str:
    return "not_applicable" if status == "image_only" else "pending"


def _extract_question_candidates(
    *,
    fitz_doc: fitz.Document,
    plumber_doc: Any | None,
    anchor: Any,
    next_anchor: Any | None,
    question_number: int,
) -> dict[str, Any]:
    page = fitz_doc[anchor.page_index]
    question_bbox = _question_text_bbox(fitz_doc, anchor, next_anchor)
    primary = _extract_with_pymupdf(page, question_bbox, question_number)
    selected = primary

    if plumber_doc is not None and _question_needs_secondary_review(primary):
        secondary = _extract_with_pdfplumber(plumber_doc.pages[anchor.page_index], question_bbox, question_number)
        if _question_candidate_score(secondary) > _question_candidate_score(primary):
            selected = {
                **primary,
                "stem_text": secondary["stem_text"],
                "choices": secondary["choices"],
                "question_method": "pdfplumber_text",
                "methods": {
                    "stem": "pdfplumber_text",
                    "choices": {label: "pdfplumber_text" for label in OPTION_LABELS},
                },
            }

    selected["page"] = anchor.page_index + 1
    selected["question_bbox"] = round_rect(question_bbox)
    selected["fitz_page"] = page
    return selected


def _extract_with_pymupdf(page: fitz.Page, bbox: fitz.Rect, question_number: int) -> dict[str, Any]:
    raw_text = page.get_text("text", clip=bbox)
    cleaned_text = _clean_question_text(raw_text)
    cleaned_text = _strip_question_number(cleaned_text, question_number)
    stem_text, parsed_choices = parse_choices(cleaned_text)
    choice_texts = {choice["label"]: choice["text"] for choice in parsed_choices}

    repaired = _repair_choices_from_layout(page, bbox)
    for label, repaired_text in repaired.items():
        if _candidate_score(repaired_text, expected_mode="text_required", asset_refs=[]) > _candidate_score(
            choice_texts.get(label, ""),
            expected_mode="text_required",
            asset_refs=[],
        ):
            choice_texts[label] = repaired_text

    field_bboxes = _estimate_field_bboxes(page, bbox)
    return {
        "stem_text": stem_text,
        "choices": choice_texts,
        "field_bboxes": field_bboxes,
        "choice_bboxes": field_bboxes["choices"],
        "question_method": "pymupdf_text",
        "methods": {
            "stem": "pymupdf_text",
            "choices": {label: "pymupdf_text" for label in OPTION_LABELS},
        },
    }


def _extract_with_pdfplumber(plumber_page: Any, bbox: fitz.Rect, question_number: int) -> dict[str, Any]:
    page_x0, page_y0, page_x1, page_y1 = plumber_page.bbox
    crop_bbox = (
        max(page_x0, min(float(bbox.x0), page_x1)),
        max(page_y0, min(float(bbox.y0), page_y1)),
        max(page_x0, min(float(bbox.x1), page_x1)),
        max(page_y0, min(float(bbox.y1), page_y1)),
    )
    crop = plumber_page.crop(crop_bbox, strict=False)
    raw_text = crop.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
    cleaned_text = _clean_question_text(raw_text)
    cleaned_text = _strip_question_number(cleaned_text, question_number)
    stem_text, parsed_choices = parse_choices(cleaned_text)
    return {
        "stem_text": stem_text,
        "choices": {choice["label"]: choice["text"] for choice in parsed_choices},
    }


def _question_needs_secondary_review(candidate: dict[str, Any]) -> bool:
    if _is_field_suspicious(candidate["stem_text"], expected_mode="text_required", asset_refs=[]):
        return True
    return any(
        _is_field_suspicious(candidate["choices"].get(label, ""), expected_mode="text_required", asset_refs=[])
        for label in OPTION_LABELS
    )


def _question_candidate_score(candidate: dict[str, Any]) -> int:
    score = _candidate_score(candidate["stem_text"], expected_mode="text_required", asset_refs=[]) * 3
    for label in OPTION_LABELS:
        score += _candidate_score(candidate["choices"].get(label, ""), expected_mode="text_required", asset_refs=[])
    return score


def _repair_choices_from_layout(page: fitz.Page, bbox: fitz.Rect) -> dict[str, str]:
    repaired: dict[str, str] = {}
    layout = _option_segments_from_rows(page.get_text("words", clip=bbox), bbox)
    for label, segment in layout.items():
        if segment["tokens"]:
            repaired[label] = collapse_inline(" ".join(segment["tokens"]))
    return repaired


def _estimate_field_bboxes(page: fitz.Page, bbox: fitz.Rect) -> dict[str, Any]:
    rows = group_words_into_rows(page.get_text("words", clip=bbox))
    stem_rects: list[fitz.Rect] = []
    choice_rects = {label: None for label in OPTION_LABELS}
    saw_option_row = False

    for row in rows:
        row_rects = [fitz.Rect(word[0], word[1], word[2], word[3]) for word in row]
        row_text = collapse_inline(" ".join(word[4] for word in row))
        if not row_text:
            continue
        if _is_noise_line(row_text):
            continue
        if _is_section_break_line(row_text):
            break

        markers = [(option_label_from_token(word[4]), word) for word in row]
        markers = [(label, word) for label, word in markers if label]
        if markers:
            saw_option_row = True
            segments = _option_segments_for_row(row, bbox)
            for label, rect in segments.items():
                if rect is None:
                    continue
                choice_rects[label] = fitz.Rect(rect) if choice_rects[label] is None else fitz.Rect(choice_rects[label]) | rect
            continue

        if not saw_option_row:
            stem_rects.extend(row_rects)

    stem_bbox = round_rect(_union_rects(stem_rects, bbox))
    choice_bboxes = {
        label: round_rect(choice_rects[label] if choice_rects[label] is not None else bbox)
        for label in OPTION_LABELS
    }
    return {"stem": stem_bbox, "choices": choice_bboxes}


def _option_segments_from_rows(
    words: list[tuple[float, float, float, float, str, int, int, int]],
    bbox: fitz.Rect,
) -> dict[str, dict[str, Any]]:
    rows = group_words_into_rows(words)
    segments = {label: {"tokens": [], "rect": None} for label in OPTION_LABELS}
    for row in rows:
        row_segments = _option_segments_for_row(row, bbox)
        for label, rect in row_segments.items():
            if rect is None:
                continue
            tokens = [
                collapse_inline(word[4])
                for word in row
                if word[0] >= rect.x0 - 0.5
                and word[2] <= rect.x1 + 0.5
                and option_label_from_token(word[4]) is None
                and collapse_inline(word[4])
            ]
            if tokens and not segments[label]["tokens"]:
                segments[label]["tokens"] = tokens
            if segments[label]["rect"] is None:
                segments[label]["rect"] = rect
            else:
                segments[label]["rect"] = fitz.Rect(segments[label]["rect"]) | rect
    return segments


def _option_segments_for_row(
    row: list[tuple[float, float, float, float, str, int, int, int]],
    bbox: fitz.Rect,
) -> dict[str, fitz.Rect | None]:
    markers = [(option_label_from_token(word[4]), word) for word in row]
    markers = [(label, word) for label, word in markers if label]
    if not markers:
        return {label: None for label in OPTION_LABELS}

    markers.sort(key=lambda item: item[1][0])
    segments = {label: None for label in OPTION_LABELS}
    for index, (label, marker) in enumerate(markers):
        start_x = marker[0]
        end_x = markers[index + 1][1][0] if index + 1 < len(markers) else bbox.x1
        segment_rects = [fitz.Rect(marker[0], marker[1], marker[2], marker[3])]
        for word in row:
            if option_label_from_token(word[4]) is not None:
                continue
            if word[0] >= marker[2] - 1.0 and word[2] <= end_x + 1.0:
                segment_rects.append(fitz.Rect(word[0], word[1], word[2], word[3]))
        segments[label] = _union_rects(segment_rects, fitz.Rect(marker[0], marker[1], end_x, marker[3]))
    return segments


def _question_text_bbox(fitz_doc: fitz.Document, anchor: Any, next_anchor: Any | None) -> fitz.Rect:
    bbox = fitz.Rect(question_bbox_for_anchor(fitz_doc, anchor, next_anchor))
    page = fitz_doc[anchor.page_index]
    footer_top = _footer_top(page)
    if footer_top is not None:
        bbox.y1 = min(bbox.y1, max(bbox.y0 + 8.0, footer_top - 6.0))
    return bbox


def _footer_top(page: fitz.Page) -> float | None:
    candidates: list[float] = []
    for block in page.get_text("blocks"):
        x0, y0, _x1, _y1, text, *_ = block
        collapsed = collapse_inline(text)
        if not collapsed or y0 < page.rect.height * 0.72:
            continue
        if _is_noise_line(collapsed):
            candidates.append(float(y0))
    if not candidates:
        return None
    return min(candidates)


def _clean_question_text(raw_text: str) -> str:
    lines = [collapse_inline(line) for line in raw_text.splitlines() if collapse_inline(line)]
    cleaned: list[str] = []
    last_option_index = -1
    for line in lines:
        if _is_noise_line(line):
            continue
        if _is_section_break_line(line):
            break
        cleaned.append(line)
        if any(f"({label})" in line for label in OPTION_LABELS):
            last_option_index = len(cleaned) - 1

    if last_option_index >= 0:
        trailing = cleaned[last_option_index + 1 :]
        if trailing and len(trailing) <= 6 and all(_looks_like_visual_sequence(line) for line in trailing):
            cleaned = cleaned[: last_option_index + 1]

    return "\n".join(cleaned).strip()


def _clean_field_text(text: str, *, expected_mode: str, asset_refs: list[str]) -> str:
    candidate = collapse_inline(text)
    candidate = re.sub(r"\s+([,.;:?!])", r"\1", candidate)
    candidate = re.sub(r"\s+\)", ")", candidate)
    candidate = re.sub(r"\(\s+", "(", candidate)
    for pattern in SUSPICIOUS_PATTERNS:
        candidate = pattern.sub("", candidate)
    candidate = collapse_inline(candidate)

    if expected_mode == "image_only":
        if _looks_like_visual_sequence(candidate):
            return ""
        if len(TEXT_TOKEN_RE.findall(candidate)) <= 1 and len(candidate) <= 3:
            return ""
    return candidate


def _classify_expected_mode(kind: str, baseline_text: str, asset_refs: list[str]) -> str:
    baseline = collapse_inline(baseline_text)
    if not asset_refs:
        return "text_required"
    if not baseline:
        return "image_only"
    if _looks_like_visual_sequence(baseline):
        return "image_only"
    if kind == "stem" and len(LETTER_WORD_RE.findall(baseline)) < 2:
        return "image_only"
    return "text_with_image"


def _review_priority(
    *,
    baseline_text: str,
    extracted_text: str,
    expected_mode: str,
    suspicious: bool,
) -> str:
    if expected_mode == "image_only":
        return "image_only"
    if suspicious:
        return "suspicious"
    if _normalize_compare_text(baseline_text) != _normalize_compare_text(extracted_text):
        return "changed"
    return "unchanged"


def _field_confidence(method: str, text: str, suspicious: bool) -> float:
    base = 0.86
    if method.startswith("pdfplumber"):
        base = 0.9
    elif method.startswith("tesseract"):
        base = 0.72
    if not text:
        base -= 0.2
    if suspicious:
        base -= 0.25
    return max(0.05, min(0.99, base))


def _finalize_method(method: str, suspicious: bool) -> str:
    if suspicious and not method.endswith("+needs_review"):
        return f"{method}+needs_review"
    return method


def _candidate_score(text: str, *, expected_mode: str, asset_refs: list[str]) -> int:
    candidate = collapse_inline(text)
    if not candidate:
        return 5 if expected_mode == "image_only" else 0

    score = 5
    score += len(LETTER_WORD_RE.findall(candidate)) * 4
    score += len(TEXT_TOKEN_RE.findall(candidate))
    if _looks_like_visual_sequence(candidate) and asset_refs:
        score -= 30
    if _is_field_suspicious(candidate, expected_mode=expected_mode, asset_refs=asset_refs):
        score -= 40
    return score


def _is_field_suspicious(text: str, *, expected_mode: str, asset_refs: list[str]) -> bool:
    candidate = collapse_inline(text)
    if expected_mode != "image_only" and not candidate:
        return True
    if not candidate:
        return False
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(candidate):
            return True
    if SPACED_SINGLE_CHAR_RE.fullmatch(candidate) and asset_refs:
        return True
    tokens = candidate.split()
    if tokens and len(tokens) >= 4 and all(len(token) <= 2 for token in tokens) and asset_refs:
        return True
    if len(TEXT_TOKEN_RE.findall(candidate)) >= 6 and len(LETTER_WORD_RE.findall(candidate)) == 0 and asset_refs:
        return True
    return False


def _is_noise_line(line: str) -> bool:
    collapsed = collapse_inline(line)
    if not collapsed:
        return True
    if NOISE_LINE_RE.search(collapsed):
        return True
    return bool(re.search(r"\bDo not duplicate\b", collapsed, flags=re.IGNORECASE))


def _is_section_break_line(line: str) -> bool:
    return bool(SECTION_BREAK_RE.match(collapse_inline(line)))


def _looks_like_visual_sequence(text: str) -> bool:
    candidate = collapse_inline(text)
    if not candidate:
        return False
    tokens = candidate.split()
    if len(tokens) >= 3 and all(len(re.sub(r"[^A-Za-z0-9]", "", token)) <= 1 for token in tokens):
        return True
    return bool(TRAILING_OPTION_NOISE_RE.fullmatch(candidate) and len(tokens) >= 3)


def _normalize_compare_text(text: str) -> str:
    normalized = collapse_inline(text).lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _strip_question_number(text: str, question_number: int) -> str:
    return re.sub(rf"^\s*{question_number}\.\s*", "", text, count=1)


def _ocr_choice_snippet(page: fitz.Page, bbox: fitz.Rect, baseline_text: str) -> str:
    if not TESSERACT_PRESENT:
        return ""
    width = bbox.width
    height = bbox.height
    if width <= 1.0 or height <= 1.0:
        return ""

    whitelist = _ocr_whitelist(baseline_text)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), clip=bbox, alpha=False).save(temp_path.as_posix())
        command = ["tesseract", temp_path.as_posix(), "stdout", "--psm", "7"]
        if whitelist:
            command.extend(["-c", f"tessedit_char_whitelist={whitelist}"])
        result = run_tesseract_ocr(temp_path) if command == ["tesseract", temp_path.as_posix(), "stdout", "--psm", "7"] else None
        if result is None:
            import subprocess

            result = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        return collapse_inline(result)
    except Exception:
        return ""
    finally:
        temp_path.unlink(missing_ok=True)


def _ocr_whitelist(baseline_text: str) -> str:
    baseline = collapse_inline(baseline_text)
    if baseline and re.fullmatch(r"[0-9\s()+\-*/=.,:;?!]+", baseline):
        return "0123456789()+-*/=.,:;?!"
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789()+-*/=.,:;?!"


def _index_report_html(*, manifest_exams: list[dict[str, Any]], generated_at: datetime) -> str:
    cards = []
    for entry in sorted(manifest_exams, key=lambda item: item["exam_id"]):
        cards.append(
            f"""
            <article class="card">
              <h2><a href="{html.escape(entry['report_path'])}">{html.escape(entry['exam_id'])}</a></h2>
              <p>{html.escape(entry['source_pdf'])}</p>
              <dl>
                <div><dt>Fields</dt><dd>{entry['field_count']}</dd></div>
                <div><dt>Changed</dt><dd>{entry['changed_count']}</dd></div>
                <div><dt>Suspicious</dt><dd>{entry['suspicious_count']}</dd></div>
                <div><dt>Image Only</dt><dd>{entry['image_only_count']}</dd></div>
              </dl>
            </article>
            """
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Text Diff Index</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f5f1e8; color: #171513; }}
    main {{ width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 48px; }}
    header {{ background: white; border: 1px solid #d7d0c3; border-radius: 18px; padding: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 20px; }}
    .card {{ background: white; border: 1px solid #d7d0c3; border-radius: 18px; padding: 18px; }}
    .card h2 {{ margin: 0 0 8px; font-size: 18px; }}
    .card p {{ margin: 0 0 12px; color: #5f5a52; font-size: 13px; word-break: break-all; }}
    dl {{ margin: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    dt {{ color: #5f5a52; font-size: 12px; }}
    dd {{ margin: 0; font-weight: 700; }}
    a {{ color: #1e5d91; text-decoration: none; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Question Text Diff Review</h1>
      <p>Generated at {html.escape(generated_at.isoformat())}</p>
    </header>
    <section class="grid">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""


def _exam_report_html(payload: dict[str, Any]) -> str:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for field in payload["fields"]:
        grouped.setdefault(int(field["question_number"]), []).append(field)

    kind_order = {"stem": 0, "choice": 1, "answer": 2}
    sections = []
    for question_number in sorted(grouped):
        field_cards = []
        for field in sorted(
            grouped[question_number],
            key=lambda item: (kind_order.get(item["kind"], 99), item["choice_label"] or ""),
        ):
            css_class = field["review_priority"]
            if field["kind"] == "stem":
                label = "Stem"
            elif field["kind"] == "answer":
                label = "Answer"
            else:
                label = f"Choice {field['choice_label']}"
            field_cards.append(
                f"""
                <article class="field {css_class}">
                  <div class="field-head">
                    <h3>{html.escape(label)}</h3>
                    <span>{html.escape(field['review_priority'])}</span>
                  </div>
                  <p class="meta">mode={html.escape(field['expected_mode'])} | method={html.escape(field['method'])} | page={field['page']} | confidence={field['confidence']}</p>
                  <div class="cols">
                    <section>
                      <h4>Baseline</h4>
                      <pre>{html.escape(field['baseline_text'])}</pre>
                    </section>
                    <section>
                      <h4>Extracted</h4>
                      <pre>{html.escape(field['extracted_text'])}</pre>
                    </section>
                  </div>
                  <p class="meta">bbox={html.escape(json.dumps(field['text_bbox']))} | assets={html.escape(', '.join(field['asset_refs']) or '-')}</p>
                </article>
                """
            )
        sections.append(
            f"""
            <section class="question">
              <h2>Question {question_number}</h2>
              {''.join(field_cards)}
            </section>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(payload['exam_id'])} text diff</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f6f3eb; color: #171513; }}
    main {{ width: min(1280px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 48px; }}
    header {{ background: white; border: 1px solid #d9d1c5; border-radius: 18px; padding: 22px; margin-bottom: 20px; }}
    .question {{ background: white; border: 1px solid #d9d1c5; border-radius: 18px; padding: 18px; margin-bottom: 16px; }}
    .field {{ border: 1px solid #e0d8cb; border-radius: 16px; padding: 14px; margin-top: 12px; }}
    .field.changed {{ border-color: #caa54c; background: #fff9eb; }}
    .field.suspicious {{ border-color: #bf5a4a; background: #fff0ed; }}
    .field.unchanged {{ border-color: #93a483; background: #f4f9ef; }}
    .field.image_only {{ border-color: #7a8fa8; background: #f1f6fb; }}
    .field-head {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
    .field-head h3 {{ margin: 0; }}
    .field-head span {{ text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em; color: #5f5a52; }}
    .cols {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: rgba(255,255,255,0.7); border-radius: 12px; padding: 12px; margin: 0; min-height: 52px; }}
    .meta {{ color: #5f5a52; font-size: 12px; margin: 8px 0 0; }}
    a {{ color: #1e5d91; text-decoration: none; }}
  </style>
</head>
<body>
  <main>
    <header>
      <p><a href="index.html">Back to index</a></p>
      <h1>{html.escape(payload['exam_id'])}</h1>
      <p>{html.escape(payload['source_pdf'])}</p>
    </header>
    {''.join(sections)}
  </main>
</body>
</html>
"""


def _select_exam_ids(manifest: dict[str, Any], exam_ids: list[str] | None) -> list[str]:
    selected = set(exam_ids or [])
    exam_entries = manifest.get("exams", [])
    ids = [entry["exam_id"] for entry in exam_entries if not selected or entry["exam_id"] in selected]
    if selected:
        known = {entry["exam_id"] for entry in exam_entries}
        missing = sorted(selected - known)
        if missing:
            raise TextReviewValidationError(f"Unknown exam_id values: {', '.join(missing)}")
    if not ids:
        raise TextReviewValidationError("No exams matched the requested text review scope.")
    return ids


def _validate_exact_keys(payload: dict[str, Any], expected_keys: set[str], label: str) -> None:
    actual = set(payload.keys())
    if actual != expected_keys:
        raise TextReviewValidationError(
            f"{label} has unexpected keys: expected {sorted(expected_keys)}, got {sorted(actual)}"
        )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _union_rects(rects: list[fitz.Rect], fallback: fitz.Rect) -> fitz.Rect:
    if not rects:
        return fitz.Rect(fallback)
    rect = fitz.Rect(rects[0])
    for other in rects[1:]:
        rect |= other
    return rect
