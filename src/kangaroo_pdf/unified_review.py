from __future__ import annotations

import html
import json
import mimetypes
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import quote, unquote

import fitz

from .pipeline import classify_document, classify_documents, collapse_inline, extract_answers, round_rect
from .text_review_pipeline import (
    SCHEMA_VERSION as TEXT_REVIEW_SCHEMA_VERSION,
    _build_field_record,
    _field_confidence,
    _finalize_method,
    _is_field_suspicious,
)

REVIEW_STATUS_VALUES = ("pending", "approved", "needs_review", "not_applicable")
REVIEW_STATUS_SET = set(REVIEW_STATUS_VALUES)


class ReviewHTTPError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass
class UnifiedReviewRepository:
    data_dir: Path
    review_dir: Path
    release_dir: Path | None = None
    cache_dir: Path | None = None
    _answer_field_cache: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.data_dir = self.data_dir.resolve()
        self.review_dir = self.review_dir.resolve()
        self.release_dir = self.release_dir.resolve() if self.release_dir else None
        default_cache = Path(tempfile.gettempdir()) / f"{self.data_dir.parent.name}-unified-review-cache"
        self.cache_dir = (self.cache_dir or default_cache).resolve()

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "manifest.json"

    @property
    def report_dir(self) -> Path:
        return self.data_dir.parent / "reports" / "text-diff"

    def manifest(self) -> dict[str, Any]:
        return _read_json(self.manifest_path)

    def exam_entries(self) -> list[dict[str, Any]]:
        return list(self.manifest().get("exams", []))

    def exam_paths(self, exam_id: str) -> tuple[Path, Path]:
        exam_dir = self.data_dir / "exams" / exam_id
        return exam_dir / "exam.json", exam_dir / "audit.json"

    def review_path(self, exam_id: str) -> Path:
        return self.review_dir / f"{exam_id}.json"

    def exam_bundle(self, exam_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        exam_path, audit_path = self.exam_paths(exam_id)
        if not exam_path.exists() or not audit_path.exists():
            raise ReviewHTTPError(404, f"Exam {exam_id} was not found.")
        return _read_json(exam_path), _read_json(audit_path)

    def list_exam_summaries(self) -> dict[str, Any]:
        summaries = []
        totals = Counter()
        for entry in self.exam_entries():
            exam_id = entry["exam_id"]
            exam_json, _audit_json = self.exam_bundle(exam_id)
            review_doc = self.load_review_document(exam_id, exam_json=exam_json, include_answer_fields=False)
            counts = _field_counts(review_doc["fields"])
            summaries.append(
                {
                    "exam_id": exam_id,
                    "question_count": exam_json["question_count"],
                    "field_count": len(review_doc["fields"]),
                    "changed_count": counts["priorities"]["changed"],
                    "suspicious_count": counts["priorities"]["suspicious"],
                    "pending_count": counts["review_statuses"]["pending"],
                    "needs_review_count": counts["review_statuses"]["needs_review"],
                    "approved_count": counts["review_statuses"]["approved"],
                    "not_applicable_count": counts["review_statuses"]["not_applicable"],
                    "source_pdf": exam_json["source_pdf"],
                    "detail_url": f"/exams/{quote(exam_id)}",
                    "api_url": f"/api/exams/{quote(exam_id)}",
                    "legacy_report_exists": (self.report_dir / f"{exam_id}.html").exists(),
                }
            )
            totals.update(
                {
                    "exams": 1,
                    "questions": exam_json["question_count"],
                    "fields": len(review_doc["fields"]),
                    "changed": counts["priorities"]["changed"],
                    "suspicious": counts["priorities"]["suspicious"],
                    "pending": counts["review_statuses"]["pending"],
                    "needs_review": counts["review_statuses"]["needs_review"],
                    "approved": counts["review_statuses"]["approved"],
                }
            )
        return {
            "generated_at": self.manifest().get("generated_at"),
            "counts": dict(totals),
            "exams": summaries,
        }

    def load_review_document(
        self,
        exam_id: str,
        *,
        exam_json: dict[str, Any] | None = None,
        include_answer_fields: bool,
    ) -> dict[str, Any]:
        if exam_json is None:
            exam_json, _ = self.exam_bundle(exam_id)
        path = self.review_path(exam_id)
        payload = _read_json(path) if path.exists() else {}
        raw_fields = payload.get("fields", [])
        fields = [_normalize_review_field(field) for field in raw_fields if isinstance(field, dict)]

        if include_answer_fields:
            existing_answer_fields = {field["field_id"] for field in fields if field["kind"] == "answer"}
            if len(existing_answer_fields) < len(exam_json["questions"]):
                synthesized = self.answer_fields(exam_json)
                by_id = {field["field_id"]: field for field in fields}
                for field in synthesized:
                    by_id.setdefault(field["field_id"], field)
                fields = list(by_id.values())

        fields = sorted(fields, key=_field_sort_key)
        return {
            "schema_version": TEXT_REVIEW_SCHEMA_VERSION,
            "generated_at": payload.get("generated_at") or _utc_now_iso(),
            "exam_id": exam_id,
            "source_pdf": exam_json["source_pdf"],
            "question_count": len(exam_json["questions"]),
            "field_count": len(fields),
            "fields": fields,
        }

    def answer_fields(self, exam_json: dict[str, Any]) -> list[dict[str, Any]]:
        exam_id = exam_json["exam_id"]
        if exam_id in self._answer_field_cache:
            return [dict(field) for field in self._answer_field_cache[exam_id]]

        source_pdf = self.source_pdf_path(exam_json)
        document = classify_document(source_pdf)
        answer_documents = {doc.year: doc for doc in classify_documents(source_pdf.parent) if doc.is_answer_table}
        with fitz.open(source_pdf.as_posix()) as fitz_doc:
            answer_payload = extract_answers(document, fitz_doc, answer_documents.get(document.year))

        fields: list[dict[str, Any]] = []
        for question in exam_json["questions"]:
            number_key = str(question["number"])
            extracted_text = collapse_inline(answer_payload["answers"].get(number_key, ""))
            suspicious = _is_field_suspicious(extracted_text, expected_mode="text_required", asset_refs=[])
            method = _finalize_method(answer_payload["method"], suspicious)
            confidence = float(answer_payload["confidence_by_question"].get(number_key, 0.0))
            if not confidence:
                confidence = _field_confidence(answer_payload["method"], extracted_text, suspicious)
            fields.append(
                _build_field_record(
                    field_id=f"q{question['number']:02d}.answer",
                    question_number=question["number"],
                    kind="answer",
                    choice_label=None,
                    expected_mode="text_required",
                    baseline_text=question.get("answer", "") or "",
                    extracted_text=extracted_text,
                    method=method,
                    confidence=confidence,
                    page=int(answer_payload.get("page_by_question", {}).get(number_key, 1)),
                    text_bbox=list(answer_payload.get("bbox_by_question", {}).get(number_key, [])),
                    asset_refs=[],
                )
            )

        self._answer_field_cache[exam_id] = [dict(field) for field in fields]
        return fields

    def exam_detail(self, exam_id: str) -> dict[str, Any]:
        exam_json, audit_json = self.exam_bundle(exam_id)
        review_doc = self.load_review_document(exam_id, exam_json=exam_json, include_answer_fields=True)
        review_fields = review_doc["fields"]
        field_counts = _field_counts(review_fields)
        audit_lookup = {int(question["number"]): question for question in audit_json.get("questions", [])}
        asset_lookup = {asset["id"]: asset for asset in exam_json.get("assets", [])}
        fields_by_question: dict[int, list[dict[str, Any]]] = {}
        for field in review_fields:
            fields_by_question.setdefault(int(field["question_number"]), []).append(field)

        page_sizes = self.page_sizes(exam_json)
        question_views = []
        for question in exam_json["questions"]:
            number = int(question["number"])
            audit_question = audit_lookup.get(number, {})
            page_number = int(audit_question.get("page", 1))
            field_views = []
            for field in sorted(fields_by_question.get(number, []), key=_field_sort_key):
                field_asset_views = [
                    self.asset_view(exam_id, asset_lookup.get(asset_id))
                    for asset_id in field.get("asset_refs", [])
                    if asset_lookup.get(asset_id)
                ]
                decorated = dict(field)
                decorated["label"] = _field_label(field)
                decorated["asset_views"] = field_asset_views
                field_views.append(decorated)

            stem_assets = [
                self.asset_view(exam_id, asset_lookup.get(asset_id))
                for asset_id in question.get("shared_asset_refs", [])
                if asset_lookup.get(asset_id)
            ]
            option_assets = {}
            for choice in question.get("choices", []):
                option_assets[choice["label"]] = [
                    self.asset_view(exam_id, asset_lookup.get(asset_id))
                    for asset_id in choice.get("asset_refs", [])
                    if asset_lookup.get(asset_id)
                ]

            question_views.append(
                {
                    "number": number,
                    "page": page_number,
                    "page_image_url": f"/artifacts/pages/{quote(exam_id)}/{page_number}.png",
                    "page_rect": page_sizes.get(page_number, []),
                    "reference_bbox": list(audit_question.get("reference_bbox", [])),
                    "text_bbox": list(audit_question.get("text_bbox", [])),
                    "needs_review": bool(audit_question.get("needs_review")),
                    "answer": question.get("answer") or "",
                    "answer_confidence": float(audit_question.get("answer_confidence", 0.0)),
                    "field_views": field_views,
                    "stem_text": question.get("stem_text", ""),
                    "stem_assets": stem_assets,
                    "option_assets": option_assets,
                    "choices": question.get("choices", []),
                    "question_counts": _field_counts(field_views),
                }
            )

        return {
            "exam_id": exam_id,
            "source_pdf": exam_json["source_pdf"],
            "question_count": exam_json["question_count"],
            "field_count": len(review_fields),
            "counts": field_counts,
            "answer_source": audit_json.get("answer_source", {}),
            "question_views": question_views,
        }

    def save_field_review(self, exam_id: str, field_id: str, review_status: str, review_notes: str) -> dict[str, Any]:
        if review_status not in REVIEW_STATUS_SET:
            raise ReviewHTTPError(400, f"Invalid review_status {review_status!r}.")

        exam_json, _audit_json = self.exam_bundle(exam_id)
        review_doc = self.load_review_document(exam_id, exam_json=exam_json, include_answer_fields=True)
        updated_field = None
        for field in review_doc["fields"]:
            if field["field_id"] != field_id:
                continue
            field["review_status"] = review_status
            field["review_notes"] = review_notes
            field["reviewed_at"] = None if review_status == "pending" else _utc_now_iso()
            updated_field = dict(field)
            break
        if updated_field is None:
            raise ReviewHTTPError(404, f"Field {field_id} was not found.")

        review_doc["field_count"] = len(review_doc["fields"])
        _write_json(self.review_path(exam_id), review_doc)
        return {
            "field": updated_field,
            "counts": _field_counts(review_doc["fields"]),
        }

    def source_pdf_path(self, exam_json: dict[str, Any]) -> Path:
        source_pdf = Path(exam_json["source_pdf"])
        if source_pdf.is_absolute():
            return source_pdf
        return (self.data_dir.parent / source_pdf).resolve()

    def page_sizes(self, exam_json: dict[str, Any]) -> dict[int, list[float]]:
        source_pdf = self.source_pdf_path(exam_json)
        sizes: dict[int, list[float]] = {}
        with fitz.open(source_pdf.as_posix()) as doc:
            for index, page in enumerate(doc, start=1):
                sizes[index] = round_rect(page.rect)
        return sizes

    def rendered_page_path(self, exam_id: str, page_number: int) -> Path:
        exam_json, _ = self.exam_bundle(exam_id)
        source_pdf = self.source_pdf_path(exam_json)
        cache_path = self.cache_dir / exam_id / f"page-{page_number}.png"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists() and cache_path.stat().st_mtime >= source_pdf.stat().st_mtime:
            return cache_path

        with fitz.open(source_pdf.as_posix()) as doc:
            if page_number < 1 or page_number > len(doc):
                raise ReviewHTTPError(404, f"Page {page_number} was not found for {exam_id}.")
            page = doc[page_number - 1]
            page.get_pixmap(matrix=fitz.Matrix(1.7, 1.7), alpha=False).save(cache_path.as_posix())
        return cache_path

    def asset_view(self, exam_id: str, asset: dict[str, Any] | None) -> dict[str, Any]:
        if not asset:
            return {"id": "", "path": "", "url": None, "exists": False, "role": ""}
        resolved = self.resolve_asset_path(exam_id, asset["path"])
        return {
            "id": asset["id"],
            "path": asset["path"],
            "role": asset.get("role", ""),
            "exists": resolved is not None,
            "url": f"/artifacts/assets/{quote(exam_id)}/{quote(asset['id'])}" if resolved else None,
        }

    def resolve_asset_path(self, exam_id: str, relative_path: str) -> Path | None:
        candidates = [self.data_dir / "exams" / exam_id / relative_path]
        if self.release_dir is not None:
            candidates.append(self.release_dir / "exams" / exam_id / relative_path)
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def asset_path_for_id(self, exam_id: str, asset_id: str) -> Path:
        exam_json, _ = self.exam_bundle(exam_id)
        asset_lookup = {asset["id"]: asset for asset in exam_json.get("assets", [])}
        asset = asset_lookup.get(asset_id)
        if asset is None:
            raise ReviewHTTPError(404, f"Asset {asset_id} was not found for {exam_id}.")
        resolved = self.resolve_asset_path(exam_id, asset["path"])
        if resolved is None:
            raise ReviewHTTPError(404, f"Asset {asset_id} is missing on disk.")
        return resolved


def create_unified_review_app(
    data_dir: Path | str,
    review_dir: Path | str,
    release_dir: Path | str | None = None,
    cache_dir: Path | str | None = None,
) -> Callable[[dict[str, Any], Callable[..., Any]], Iterable[bytes]]:
    repository = UnifiedReviewRepository(
        data_dir=Path(data_dir),
        review_dir=Path(review_dir),
        release_dir=Path(release_dir).resolve() if release_dir else None,
        cache_dir=Path(cache_dir).resolve() if cache_dir else None,
    )

    def app(environ: dict[str, Any], start_response: Callable[..., Any]) -> Iterable[bytes]:
        try:
            method = environ.get("REQUEST_METHOD", "GET").upper()
            path = environ.get("PATH_INFO", "/") or "/"
            response = _route_request(repository, method, path, environ)
        except ReviewHTTPError as error:
            response = _json_response(error.status_code, {"error": error.message})
        except Exception as error:  # pragma: no cover - defensive fallback
            response = _json_response(500, {"error": str(error)})

        start_response(response["status"], response["headers"])
        return [response["body"]]

    return app


def _route_request(
    repository: UnifiedReviewRepository,
    method: str,
    path: str,
    environ: dict[str, Any],
) -> dict[str, Any]:
    normalized = path.rstrip("/") or "/"
    segments = [unquote(segment) for segment in normalized.split("/") if segment]

    if method == "GET" and normalized == "/":
        payload = repository.list_exam_summaries()
        return _html_response(200, _index_html(payload))

    if method == "GET" and len(segments) == 2 and segments[0] == "exams":
        detail = repository.exam_detail(segments[1])
        return _html_response(200, _exam_html(detail))

    if method == "GET" and len(segments) == 3 and segments[0] == "api" and segments[1] == "exams":
        return _json_response(200, repository.exam_detail(segments[2]))

    if (
        method == "POST"
        and len(segments) == 6
        and segments[0] == "api"
        and segments[1] == "exams"
        and segments[3] == "fields"
        and segments[5] == "review"
    ):
        payload = _parse_request_json(environ)
        return _json_response(
            200,
            repository.save_field_review(
                segments[2],
                segments[4],
                review_status=str(payload.get("review_status", "")),
                review_notes=str(payload.get("review_notes", "")),
            ),
        )

    if method == "GET" and len(segments) == 4 and segments[0] == "artifacts" and segments[1] == "pages":
        page_token = segments[3]
        if not page_token.endswith(".png"):
            raise ReviewHTTPError(404, "Unknown artifact path.")
        page_number = int(page_token[:-4])
        return _file_response(repository.rendered_page_path(segments[2], page_number))

    if method == "GET" and len(segments) == 4 and segments[0] == "artifacts" and segments[1] == "assets":
        return _file_response(repository.asset_path_for_id(segments[2], segments[3]))

    raise ReviewHTTPError(404, f"Unknown route {path!r}.")


def _parse_request_json(environ: dict[str, Any]) -> dict[str, Any]:
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as error:  # pragma: no cover - defensive
        raise ReviewHTTPError(400, "Invalid Content-Length header.") from error
    body = environ.get("wsgi.input", BytesIO()).read(length)
    if not body:
        return {}
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise ReviewHTTPError(400, "Request body must be valid JSON.") from error
    if not isinstance(payload, dict):
        raise ReviewHTTPError(400, "Request JSON must be an object.")
    return payload


def _json_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return {
        "status": f"{status_code} {_reason_phrase(status_code)}",
        "headers": [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))],
        "body": body,
    }


def _html_response(status_code: int, body_text: str) -> dict[str, Any]:
    body = body_text.encode("utf-8")
    return {
        "status": f"{status_code} {_reason_phrase(status_code)}",
        "headers": [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
        "body": body,
    }


def _file_response(path: Path) -> dict[str, Any]:
    body = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {
        "status": "200 OK",
        "headers": [("Content-Type", content_type), ("Content-Length", str(len(body)))],
        "body": body,
    }


def _reason_phrase(status_code: int) -> str:
    return {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    }.get(status_code, "OK")


def _normalize_review_field(field: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(field)
    normalized["verified_text"] = str(normalized.get("verified_text", "") or "")
    status = str(normalized.get("status", "pending") or "pending")
    normalized["status"] = status
    review_status = normalized.get("review_status")
    if review_status not in REVIEW_STATUS_SET:
        review_status = "not_applicable" if status == "image_only" else "pending"
    normalized["review_status"] = review_status
    normalized["review_notes"] = str(normalized.get("review_notes", "") or "")
    reviewed_at = normalized.get("reviewed_at")
    normalized["reviewed_at"] = reviewed_at if isinstance(reviewed_at, str) or reviewed_at is None else None
    normalized["choice_label"] = normalized.get("choice_label")
    normalized["asset_refs"] = list(normalized.get("asset_refs", []))
    normalized["text_bbox"] = [float(value) for value in normalized.get("text_bbox", [])]
    return normalized


def _field_sort_key(field: dict[str, Any]) -> tuple[int, int, str]:
    kind_order = {"stem": 0, "choice": 1, "answer": 2}
    return (int(field.get("question_number", 0)), kind_order.get(field.get("kind", ""), 99), field.get("choice_label") or "")


def _field_counts(fields: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    priorities = Counter(field.get("review_priority", "") for field in fields)
    review_statuses = Counter(field.get("review_status", "pending") for field in fields)
    return {
        "priorities": {
            "changed": int(priorities.get("changed", 0)),
            "suspicious": int(priorities.get("suspicious", 0)),
            "unchanged": int(priorities.get("unchanged", 0)),
            "image_only": int(priorities.get("image_only", 0)),
        },
        "review_statuses": {
            "pending": int(review_statuses.get("pending", 0)),
            "approved": int(review_statuses.get("approved", 0)),
            "needs_review": int(review_statuses.get("needs_review", 0)),
            "not_applicable": int(review_statuses.get("not_applicable", 0)),
        },
    }


def _field_label(field: dict[str, Any]) -> str:
    if field["kind"] == "stem":
        return "Stem"
    if field["kind"] == "answer":
        return "Answer"
    return f"Choice {field['choice_label']}"


def _index_html(payload: dict[str, Any]) -> str:
    cards = []
    for exam in payload["exams"]:
        cards.append(
            f"""
            <a class="card" href="{html.escape(exam['detail_url'])}">
              <h2>{html.escape(exam['exam_id'])}</h2>
              <p>{html.escape(exam['source_pdf'])}</p>
              <dl>
                <div><dt>Questions</dt><dd>{exam['question_count']}</dd></div>
                <div><dt>Fields</dt><dd>{exam['field_count']}</dd></div>
                <div><dt>Changed</dt><dd>{exam['changed_count']}</dd></div>
                <div><dt>Suspicious</dt><dd>{exam['suspicious_count']}</dd></div>
                <div><dt>Pending</dt><dd>{exam['pending_count']}</dd></div>
                <div><dt>Needs Review</dt><dd>{exam['needs_review_count']}</dd></div>
              </dl>
            </a>
            """
        )
    counts = payload["counts"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Unified Exam Review</title>
  <style>
    body {{ margin: 0; font-family: "Avenir Next", "Helvetica Neue", Arial, sans-serif; background: #f4efe5; color: #171513; }}
    main {{ width: min(1200px, calc(100vw - 32px)); margin: 0 auto; padding: 32px 0 56px; }}
    header {{ background: rgba(255,255,255,0.9); border: 1px solid rgba(23,21,19,0.12); border-radius: 24px; padding: 24px; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 18px; }}
    .stat {{ background: rgba(23,21,19,0.03); border-radius: 16px; padding: 14px; }}
    .stat strong {{ display: block; font-size: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 20px; }}
    .card {{ display: block; padding: 18px; border-radius: 22px; border: 1px solid rgba(23,21,19,0.12); background: rgba(255,255,255,0.9); color: inherit; text-decoration: none; box-shadow: 0 16px 32px rgba(16, 14, 10, 0.06); }}
    .card h2 {{ margin: 0 0 8px; font-size: 20px; }}
    .card p {{ margin: 0 0 14px; color: #60584d; font-size: 13px; word-break: break-all; }}
    dl {{ margin: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
    dt {{ color: #60584d; font-size: 12px; }}
    dd {{ margin: 0; font-weight: 700; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Unified PDF / Text / Image Review</h1>
      <p>Generated from local dataset and text verification sidecars.</p>
      <div class="stats">
        <div class="stat"><span>Exams</span><strong>{counts.get('exams', 0)}</strong></div>
        <div class="stat"><span>Questions</span><strong>{counts.get('questions', 0)}</strong></div>
        <div class="stat"><span>Fields</span><strong>{counts.get('fields', 0)}</strong></div>
        <div class="stat"><span>Changed</span><strong>{counts.get('changed', 0)}</strong></div>
        <div class="stat"><span>Suspicious</span><strong>{counts.get('suspicious', 0)}</strong></div>
        <div class="stat"><span>Pending</span><strong>{counts.get('pending', 0)}</strong></div>
      </div>
    </header>
    <section class="grid">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""


def _exam_html(payload: dict[str, Any]) -> str:
    question_sections = []
    for question in payload["question_views"]:
        question_sections.append(_question_html(payload["exam_id"], question, payload["answer_source"]))

    counts = payload["counts"]
    answer_source_excerpt = html.escape(payload["answer_source"].get("raw_excerpt") or "(empty)")
    answer_source_method = html.escape(payload["answer_source"].get("method") or "-")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(payload['exam_id'])} unified review</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --card: rgba(255,255,255,0.92);
      --line: rgba(22,21,19,0.12);
      --ink: #191713;
      --muted: #655d53;
      --accent: #1f5d8f;
      --changed: #c79126;
      --suspicious: #bf5540;
      --unchanged: #7b9a62;
      --image-only: #6b89a8;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Avenir Next", "Helvetica Neue", Arial, sans-serif; background: var(--bg); color: var(--ink); }}
    main {{ width: min(1480px, calc(100vw - 28px)); margin: 0 auto; padding: 24px 0 56px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    header {{ background: var(--card); border: 1px solid var(--line); border-radius: 24px; padding: 24px; box-shadow: 0 18px 32px rgba(20, 17, 12, 0.08); }}
    header h1 {{ margin: 8px 0 8px; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 18px; }}
    .stat {{ background: rgba(20,17,12,0.04); border-radius: 16px; padding: 14px; }}
    .stat strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; padding: 16px; border-radius: 20px; border: 1px solid var(--line); background: rgba(255,255,255,0.82); }}
    .toolbar label {{ display: grid; gap: 6px; font-size: 12px; color: var(--muted); }}
    select {{ min-width: 180px; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); background: white; font: inherit; color: var(--ink); }}
    .excerpt {{ margin-top: 14px; padding: 14px; border-radius: 16px; background: rgba(31,93,143,0.06); border: 1px solid rgba(31,93,143,0.12); }}
    .question {{ margin-top: 18px; padding: 18px; border-radius: 24px; border: 1px solid var(--line); background: var(--card); box-shadow: 0 18px 30px rgba(20, 17, 12, 0.07); }}
    .question-head {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 16px; }}
    .question-head h2 {{ margin: 0; }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .pill {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }}
    .pill.review {{ background: rgba(31,93,143,0.12); color: var(--accent); }}
    .pill.audit {{ background: rgba(191,85,64,0.12); color: var(--suspicious); }}
    .question-grid {{ display: grid; grid-template-columns: minmax(320px, 1.1fr) minmax(360px, 1.15fr) minmax(280px, 0.9fr); gap: 16px; }}
    .panel {{ padding: 16px; border-radius: 18px; border: 1px solid var(--line); background: rgba(255,255,255,0.82); min-width: 0; }}
    .panel h3 {{ margin: 0 0 12px; font-size: 15px; }}
    .page-frame {{ position: relative; border-radius: 16px; overflow: hidden; background: white; border: 1px solid var(--line); }}
    .page-frame img {{ display: block; width: 100%; height: auto; }}
    .highlight {{ position: absolute; border: 3px solid rgba(191,85,64,0.9); background: rgba(191,85,64,0.14); border-radius: 12px; box-shadow: 0 0 0 9999px rgba(255,255,255,0.08); pointer-events: none; }}
    .field-card {{ margin-top: 12px; padding: 14px; border-radius: 16px; border: 1px solid var(--line); background: rgba(255,255,255,0.96); }}
    .field-card[data-review-priority="changed"] {{ border-color: rgba(199,145,38,0.5); background: rgba(255,248,232,0.98); }}
    .field-card[data-review-priority="suspicious"] {{ border-color: rgba(191,85,64,0.5); background: rgba(255,240,236,0.98); }}
    .field-card[data-review-priority="unchanged"] {{ border-color: rgba(123,154,98,0.45); background: rgba(244,249,239,0.98); }}
    .field-card[data-review-priority="image_only"] {{ border-color: rgba(107,137,168,0.45); background: rgba(241,246,251,0.98); }}
    .field-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }}
    .field-head h4 {{ margin: 0; }}
    .field-meta {{ color: var(--muted); font-size: 12px; margin-top: 8px; }}
    .diff-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }}
    .diff-grid h5 {{ margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
    pre {{ margin: 0; min-height: 48px; padding: 12px; border-radius: 12px; background: rgba(245,241,233,0.72); white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; line-height: 1.5; }}
    .review-form {{ display: grid; gap: 10px; margin-top: 12px; }}
    .review-form label {{ display: grid; gap: 6px; font-size: 12px; color: var(--muted); }}
    textarea {{ min-height: 76px; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); background: white; font: inherit; resize: vertical; }}
    .review-actions {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
    button {{ padding: 10px 14px; border-radius: 999px; border: 0; background: var(--accent); color: white; font: inherit; font-weight: 700; cursor: pointer; }}
    .save-state {{ color: var(--muted); font-size: 12px; }}
    .asset-group {{ display: grid; gap: 12px; }}
    .asset-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }}
    figure {{ margin: 0; padding: 10px; border-radius: 14px; border: 1px solid var(--line); background: white; }}
    figure img {{ display: block; max-width: 100%; border-radius: 10px; background: white; }}
    figure figcaption {{ margin-top: 8px; color: var(--muted); font-size: 12px; word-break: break-all; }}
    .option-block {{ padding: 12px; border-radius: 14px; border: 1px solid var(--line); background: white; }}
    .option-block strong {{ display: block; margin-bottom: 8px; color: var(--accent); }}
    .hidden-by-filter {{ display: none !important; }}
    @media (max-width: 1180px) {{ .question-grid {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 720px) {{ .diff-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <p><a href="/">Back to exam list</a></p>
      <h1>{html.escape(payload['exam_id'])}</h1>
      <p class="meta">{html.escape(payload['source_pdf'])}</p>
      <div class="stats">
        <div class="stat"><span>Questions</span><strong>{payload['question_count']}</strong></div>
        <div class="stat"><span>Fields</span><strong>{payload['field_count']}</strong></div>
        <div class="stat"><span id="stat-changed-label">Changed</span><strong id="stat-changed">{counts['priorities']['changed']}</strong></div>
        <div class="stat"><span id="stat-suspicious-label">Suspicious</span><strong id="stat-suspicious">{counts['priorities']['suspicious']}</strong></div>
        <div class="stat"><span id="stat-pending-label">Pending</span><strong id="stat-pending">{counts['review_statuses']['pending']}</strong></div>
        <div class="stat"><span id="stat-needs-review-label">Needs Review</span><strong id="stat-needs-review">{counts['review_statuses']['needs_review']}</strong></div>
      </div>
      <div class="toolbar">
        <label>
          Diff Filter
          <select id="priority-filter">
            <option value="all">All diff states</option>
            <option value="changed">Changed</option>
            <option value="suspicious">Suspicious</option>
            <option value="unchanged">Unchanged</option>
            <option value="image_only">Image Only</option>
          </select>
        </label>
        <label>
          Review Filter
          <select id="review-filter">
            <option value="all">All review states</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="needs_review">Needs Review</option>
            <option value="not_applicable">Not Applicable</option>
          </select>
        </label>
      </div>
      <div class="excerpt">
        <strong>Answer Source</strong>
        <p class="meta">method={answer_source_method}</p>
        <pre>{answer_source_excerpt}</pre>
      </div>
    </header>
    {''.join(question_sections)}
  </main>
  <script>
    const priorityFilter = document.getElementById('priority-filter');
    const reviewFilter = document.getElementById('review-filter');

    function applyFilters() {{
      const priorityValue = priorityFilter.value;
      const reviewValue = reviewFilter.value;
      document.querySelectorAll('.question').forEach((question) => {{
        let visibleFields = 0;
        question.querySelectorAll('.field-card').forEach((card) => {{
          const matchesPriority = priorityValue === 'all' || card.dataset.reviewPriority === priorityValue;
          const matchesReview = reviewValue === 'all' || card.dataset.reviewStatus === reviewValue;
          const visible = matchesPriority && matchesReview;
          card.classList.toggle('hidden-by-filter', !visible);
          if (visible) visibleFields += 1;
        }});
        question.classList.toggle('hidden-by-filter', visibleFields === 0);
      }});
    }}

    priorityFilter.addEventListener('change', applyFilters);
    reviewFilter.addEventListener('change', applyFilters);
    applyFilters();

    function updateStats(counts) {{
      document.getElementById('stat-changed').textContent = counts.priorities.changed;
      document.getElementById('stat-suspicious').textContent = counts.priorities.suspicious;
      document.getElementById('stat-pending').textContent = counts.review_statuses.pending;
      document.getElementById('stat-needs-review').textContent = counts.review_statuses.needs_review;
    }}

    document.querySelectorAll('[data-save-review]').forEach((button) => {{
      button.addEventListener('click', async () => {{
        const card = button.closest('.field-card');
        const examId = button.dataset.examId;
        const fieldId = button.dataset.fieldId;
        const select = card.querySelector('.review-status-select');
        const notes = card.querySelector('.review-notes');
        const state = card.querySelector('.save-state');

        state.textContent = 'Saving...';
        try {{
          const response = await fetch(`/api/exams/${{encodeURIComponent(examId)}}/fields/${{encodeURIComponent(fieldId)}}/review`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
              review_status: select.value,
              review_notes: notes.value
            }})
          }});
          const payload = await response.json();
          if (!response.ok) {{
            throw new Error(payload.error || 'Failed to save review');
          }}
          card.dataset.reviewStatus = payload.field.review_status;
          card.querySelector('.review-status-pill').textContent = payload.field.review_status;
          state.textContent = payload.field.reviewed_at ? 'Saved ' + payload.field.reviewed_at : 'Saved';
          updateStats(payload.counts);
          applyFilters();
        }} catch (error) {{
          state.textContent = error.message;
        }}
      }});
    }});
  </script>
</body>
</html>
"""


def _question_html(exam_id: str, question: dict[str, Any], answer_source: dict[str, Any]) -> str:
    field_cards = "".join(_field_html(exam_id, field) for field in question["field_views"])
    highlight_style = _highlight_style(question["page_rect"], question["reference_bbox"])
    stem_assets = _asset_grid_html(question["stem_assets"], empty_label="No stem images")
    option_blocks = []
    for choice in question["choices"]:
        option_blocks.append(
            f"""
            <div class="option-block">
              <strong>Choice {html.escape(choice['label'])}</strong>
              {_asset_grid_html(question['option_assets'].get(choice['label'], []), empty_label='No option images')}
            </div>
            """
        )
    return f"""
    <section class="question" id="q{question['number']:02d}">
      <div class="question-head">
        <div>
          <h2>Question {question['number']}</h2>
          <p class="meta">Page {question['page']} | Answer {html.escape(question['answer'] or '-')} | Confidence {question['answer_confidence']}</p>
        </div>
        <div class="badge-row">
          <span class="pill review">pending {question['question_counts']['review_statuses']['pending']}</span>
          {'<span class="pill audit">audit needs review</span>' if question['needs_review'] else ''}
        </div>
      </div>
      <div class="question-grid">
        <div class="panel">
          <h3>Original PDF Page</h3>
          <div class="page-frame">
            <img loading="lazy" src="{html.escape(question['page_image_url'])}" alt="Question {question['number']} page {question['page']}" />
            <div class="highlight" style="{highlight_style}"></div>
          </div>
          <p class="field-meta">reference bbox={html.escape(json.dumps(question['reference_bbox']))} | text bbox={html.escape(json.dumps(question['text_bbox']))}</p>
        </div>
        <div class="panel">
          <h3>Extracted Text Review</h3>
          {field_cards}
        </div>
        <div class="panel">
          <div class="asset-group">
            <div>
              <h3>Stem Images</h3>
              {stem_assets}
            </div>
            <div>
              <h3>Option Images</h3>
              <div class="asset-group">{''.join(option_blocks)}</div>
            </div>
            <div>
              <h3>Answer Source Method</h3>
              <p class="meta">{html.escape(answer_source.get('method') or '-')}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
    """


def _field_html(exam_id: str, field: dict[str, Any]) -> str:
    return f"""
    <article class="field-card" data-review-priority="{html.escape(field['review_priority'])}" data-review-status="{html.escape(field['review_status'])}" id="{html.escape(field['field_id'])}">
      <div class="field-head">
        <div>
          <h4>{html.escape(field['label'])}</h4>
          <p class="field-meta">mode={html.escape(field['expected_mode'])} | method={html.escape(field['method'])} | page={field['page']} | confidence={field['confidence']}</p>
        </div>
        <div class="badge-row">
          <span class="pill review">{html.escape(field['review_priority'])}</span>
          <span class="pill review review-status-pill">{html.escape(field['review_status'])}</span>
        </div>
      </div>
      <div class="diff-grid">
        <section>
          <h5>Baseline</h5>
          <pre>{html.escape(field['baseline_text'] or '(empty)')}</pre>
        </section>
        <section>
          <h5>Extracted</h5>
          <pre>{html.escape(field['extracted_text'] or '(empty)')}</pre>
        </section>
      </div>
      <p class="field-meta">assets={html.escape(', '.join(asset['id'] for asset in field['asset_views']) or '-')} | bbox={html.escape(json.dumps(field['text_bbox']))}</p>
      <div class="review-form">
        <label>
          Review Status
          <select class="review-status-select">
            {''.join(_review_status_option_html(value, field['review_status']) for value in REVIEW_STATUS_VALUES)}
          </select>
        </label>
        <label>
          Notes
          <textarea class="review-notes">{html.escape(field['review_notes'])}</textarea>
        </label>
        <div class="review-actions">
          <button type="button" data-save-review data-exam-id="{html.escape(exam_id)}" data-field-id="{html.escape(field['field_id'])}">Save Review</button>
          <span class="save-state">{html.escape(field['reviewed_at'] or 'Not reviewed yet')}</span>
        </div>
      </div>
    </article>
    """


def _review_status_option_html(value: str, selected_value: str) -> str:
    selected = ' selected="selected"' if value == selected_value else ""
    label = value.replace("_", " ")
    return f'<option value="{html.escape(value)}"{selected}>{html.escape(label)}</option>'


def _asset_grid_html(assets: list[dict[str, Any]], *, empty_label: str) -> str:
    existing = [asset for asset in assets if asset.get("exists")]
    if not existing:
        return f'<p class="meta">{html.escape(empty_label)}</p>'
    figures = []
    for asset in existing:
        figures.append(
            f"""
            <figure>
              <img loading="lazy" src="{html.escape(asset['url'])}" alt="{html.escape(asset['id'])}" />
              <figcaption>{html.escape(asset['id'])}</figcaption>
            </figure>
            """
        )
    return f'<div class="asset-grid">{"".join(figures)}</div>'


def _highlight_style(page_rect: list[float], bbox: list[float]) -> str:
    if len(page_rect) != 4 or len(bbox) != 4:
        return "display:none;"
    page_width = max(1.0, float(page_rect[2]) - float(page_rect[0]))
    page_height = max(1.0, float(page_rect[3]) - float(page_rect[1]))
    left = ((float(bbox[0]) - float(page_rect[0])) / page_width) * 100.0
    top = ((float(bbox[1]) - float(page_rect[1])) / page_height) * 100.0
    width = ((float(bbox[2]) - float(bbox[0])) / page_width) * 100.0
    height = ((float(bbox[3]) - float(bbox[1])) / page_height) * 100.0
    return f"left:{left:.3f}%;top:{top:.3f}%;width:{width:.3f}%;height:{height:.3f}%;"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
