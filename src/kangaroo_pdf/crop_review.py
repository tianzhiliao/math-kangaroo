from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
from fastapi import HTTPException
from pydantic import BaseModel, Field

from .visual_assets import OPTION_LABELS, round_rect

MANUAL_STATUSES = ("pending", "completed", "confirmed_no_visual")
READY_STATUSES = {"completed", "confirmed_no_visual"}
MANUAL_STATUS_SET = set(MANUAL_STATUSES)
OPTION_LABEL_SET = set(OPTION_LABELS)
PAGE_CACHE_SCALE = 2.0
EXPORT_SCALE = 2.0

MANUAL_STATUS_LABELS = {
    "pending": "待处理",
    "completed": "已完成",
    "confirmed_no_visual": "确认无图",
}


class CropRegionUpdate(BaseModel):
    page: int
    bbox: list[float] = Field(default_factory=list, min_length=4, max_length=4)
    order: int = 0
    seed_asset_id: str | None = None


class CropQuestionUpdate(BaseModel):
    status: str
    stem_regions: list[CropRegionUpdate] = Field(default_factory=list)
    option_regions: dict[str, list[CropRegionUpdate]] = Field(default_factory=dict)


@dataclass(frozen=True)
class CropReviewRepository:
    data_dir: Path
    review_dir: Path

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "manifest.json"

    @property
    def manual_root(self) -> Path:
        return self.review_dir / "manual-crops"

    @property
    def page_cache_root(self) -> Path:
        return self.review_dir / "page-cache"

    def manifest(self) -> dict[str, Any]:
        return _read_json(self.manifest_path)

    def exam_entries(self) -> list[dict[str, Any]]:
        return list(self.manifest().get("exams", []))

    def exam_dir(self, exam_id: str) -> Path:
        return self.data_dir / "exams" / exam_id

    def exam_paths(self, exam_id: str) -> tuple[Path, Path]:
        exam_dir = self.exam_dir(exam_id)
        return exam_dir / "exam.json", exam_dir / "audit.json"

    def manual_doc_path(self, exam_id: str) -> Path:
        return self.manual_root / f"{exam_id}.json"

    def manual_assets_dir(self, exam_id: str) -> Path:
        return self.manual_root / exam_id / "assets"

    def page_cache_dir(self, exam_id: str) -> Path:
        return self.page_cache_root / exam_id

    def exam_urls(self, exam_id: str) -> dict[str, str]:
        return {
            "crop_review_url": f"/crop-review/{exam_id}",
            "review_url": f"/review/{exam_id}",
        }

    def load_exam_bundle(self, exam_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        exam_path, audit_path = self.exam_paths(exam_id)
        if not exam_path.exists() or not audit_path.exists():
            raise KeyError(exam_id)
        exam_json = _read_json(exam_path)
        audit_json = _read_json(audit_path)
        manual_doc = self.load_manual_document(exam_id, exam_json, audit_json)
        return exam_json, audit_json, manual_doc

    def load_manual_document(
        self,
        exam_id: str,
        exam_json: dict[str, Any],
        audit_json: dict[str, Any],
    ) -> dict[str, Any]:
        existing = _read_json(self.manual_doc_path(exam_id)) if self.manual_doc_path(exam_id).exists() else {}
        existing_questions = existing.get("questions", {})
        exam_path, audit_path = self.exam_paths(exam_id)

        merged_questions: dict[str, dict[str, Any]] = {}
        for question in exam_json["questions"]:
            key = str(question["number"])
            merged_questions[key] = _merge_manual_question(existing_questions.get(key))

        manual_doc = {
            "exam_id": exam_id,
            "updated_at": existing.get("updated_at"),
            "source_refs": {
                "exam_json": exam_path.as_posix(),
                "audit_json": audit_path.as_posix(),
                "source_pdf": exam_json.get("source_pdf"),
            },
            "source_revision": _normalize_source_revision(existing.get("source_revision")),
            "counts": {},
            "questions": merged_questions,
        }
        manual_doc["counts"] = _count_manual_statuses(manual_doc["questions"])
        if not manual_doc["updated_at"]:
            manual_doc["updated_at"] = _latest_manual_updated_at(manual_doc["questions"])
        return manual_doc

    def list_exam_summaries(self) -> dict[str, Any]:
        manifest = self.manifest()
        summaries: list[dict[str, Any]] = []
        total_counts = {"exams": 0, "total_questions": 0, "pending": 0, "completed": 0, "confirmed_no_visual": 0, "ready": 0}
        likely_visual_total = 0
        stale_total = 0

        for entry in self.exam_entries():
            exam_id = entry["exam_id"]
            exam_json, audit_json, manual_doc = self.load_exam_bundle(exam_id)
            summary = self.build_exam_summary(exam_id, exam_json, audit_json, manual_doc)
            summaries.append(summary)
            total_counts["exams"] += 1
            total_counts["total_questions"] += summary["question_count"]
            total_counts["pending"] += summary["counts"]["pending"]
            total_counts["completed"] += summary["counts"]["completed"]
            total_counts["confirmed_no_visual"] += summary["counts"]["confirmed_no_visual"]
            total_counts["ready"] += summary["counts"]["ready"]
            likely_visual_total += summary["likely_visual_questions"]
            stale_total += summary["stale_question_count"]

        total_counts["progress_percent"] = round(
            (total_counts["ready"] / total_counts["total_questions"]) * 100, 1
        ) if total_counts["total_questions"] else 0.0

        return {
            "generated_at": manifest.get("generated_at"),
            "schema": _crop_review_schema(),
            "counts": total_counts,
            "likely_visual_questions": likely_visual_total,
            "stale_question_count": stale_total,
            "exams": summaries,
        }

    def build_exam_summary(
        self,
        exam_id: str,
        exam_json: dict[str, Any],
        audit_json: dict[str, Any],
        manual_doc: dict[str, Any],
    ) -> dict[str, Any]:
        current_revision = _source_revision(*self.exam_paths(exam_id))
        likely_visual_count = 0
        stale_count = 0
        pending_candidates: list[int] = []
        pending_any: list[int] = []

        audit_lookup = {item["number"]: item for item in audit_json["questions"]}
        for question in exam_json["questions"]:
            number = question["number"]
            audit_question = audit_lookup[number]
            if _question_is_likely_visual(question, audit_question):
                likely_visual_count += 1
                if manual_doc["questions"][str(number)]["status"] == "pending":
                    pending_candidates.append(number)
            if manual_doc["questions"][str(number)]["status"] == "pending":
                pending_any.append(number)
            if _manual_question_is_stale(manual_doc["questions"][str(number)], current_revision):
                stale_count += 1

        continue_question = pending_candidates[0] if pending_candidates else (pending_any[0] if pending_any else 1)
        counts = manual_doc["counts"]
        return {
            "exam_id": exam_id,
            "family": exam_json["family"],
            "year": exam_json["year"],
            "question_count": len(exam_json["questions"]),
            "counts": counts,
            "likely_visual_questions": likely_visual_count,
            "stale_question_count": stale_count,
            "progress_percent": round((counts["ready"] / len(exam_json["questions"])) * 100, 1)
            if exam_json["questions"]
            else 0.0,
            "updated_at": manual_doc.get("updated_at"),
            "continue_question": continue_question,
            "crop_review_url": self.exam_urls(exam_id)["crop_review_url"],
            "continue_url": f"{self.exam_urls(exam_id)['crop_review_url']}?question={continue_question}",
            "review_url": self.exam_urls(exam_id)["review_url"],
        }

    def exam_detail(self, exam_id: str) -> dict[str, Any]:
        exam_json, audit_json, manual_doc = self.load_exam_bundle(exam_id)
        asset_lookup = {asset["id"]: asset for asset in exam_json["assets"]}
        audit_lookup = {question["number"]: question for question in audit_json["questions"]}
        page_lookup = self.ensure_page_cache(exam_id, exam_json)
        current_revision = _source_revision(*self.exam_paths(exam_id))

        question_views: list[dict[str, Any]] = []
        for question in exam_json["questions"]:
            audit_question = audit_lookup[question["number"]]
            manual_question = manual_doc["questions"][str(question["number"])]
            seed_regions = _seed_regions_for_question(exam_id, question, asset_lookup, self.data_dir)
            question_views.append(
                {
                    "number": question["number"],
                    "id": question["id"],
                    "part": question["part"],
                    "points": question["points"],
                    "answer": question.get("answer"),
                    "stem_text": question.get("stem_text", ""),
                    "page": question["source"]["page"],
                    "page_image_url": page_lookup[question["source"]["page"]]["image_url"],
                    "page_meta": page_lookup[question["source"]["page"]],
                    "question_bbox": audit_question.get("reference_bbox") or question["source"].get("bbox") or [],
                    "text_bbox": audit_question.get("text_bbox") or [],
                    "likely_visual": _question_is_likely_visual(question, audit_question),
                    "seed_regions": seed_regions,
                    "manual": _manual_question_view(exam_id, manual_question, current_revision),
                    "effective_assets": _effective_assets_view(
                        exam_id,
                        question,
                        manual_question,
                        asset_lookup,
                        self.data_dir,
                        self.manual_root,
                        current_revision,
                    ),
                    "source": question["source"],
                    "audit": audit_question,
                    "system_hints": _question_hints(question, audit_question),
                    "qa_anchor_url": f"/review-files/qa/{exam_id}/index.html#q{question['number']:02d}",
                    "review_url": f"/review/{exam_id}?question={question['number']}",
                }
            )

        summary = self.build_exam_summary(exam_id, exam_json, audit_json, manual_doc)
        return {
            "schema": _crop_review_schema(),
            "meta": {
                **summary,
                "exam_id": exam_id,
                "review_url": f"/review/{exam_id}",
                "overview_url": "/crop-review",
                "source_revision": manual_doc.get("source_revision"),
                "current_source_revision": current_revision,
                "page_count": len(page_lookup),
            },
            "pages": list(page_lookup.values()),
            "exam": exam_json,
            "audit": audit_json,
            "manual": manual_doc,
            "question_views": question_views,
        }

    def save_question_annotation(
        self,
        exam_id: str,
        question_number: int,
        payload: CropQuestionUpdate,
    ) -> dict[str, Any]:
        exam_json, audit_json, manual_doc = self.load_exam_bundle(exam_id)
        question_lookup = {question["number"]: question for question in exam_json["questions"]}
        audit_lookup = {question["number"]: question for question in audit_json["questions"]}
        question = question_lookup.get(question_number)
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {question_number} was not found.")

        current_revision = _source_revision(*self.exam_paths(exam_id))
        normalized = self._normalize_and_export_payload(exam_id, question_number, payload, exam_json, audit_json)
        normalized["updated_at"] = _utc_now_iso()
        normalized["source_revision"] = current_revision

        manual_doc["questions"][str(question_number)] = normalized
        manual_doc["counts"] = _count_manual_statuses(manual_doc["questions"])
        manual_doc["updated_at"] = normalized["updated_at"]
        manual_doc["source_revision"] = current_revision
        _write_json(self.manual_doc_path(exam_id), manual_doc)

        page_lookup = self.ensure_page_cache(exam_id, exam_json)
        return {
            "question": {
                "number": question_number,
                "page": question["source"]["page"],
                "page_image_url": page_lookup[question["source"]["page"]]["image_url"],
                "page_meta": page_lookup[question["source"]["page"]],
                "question_bbox": audit_lookup[question_number].get("reference_bbox") or question["source"].get("bbox") or [],
                "text_bbox": audit_lookup[question_number].get("text_bbox") or [],
                "likely_visual": _question_is_likely_visual(question, audit_lookup[question_number]),
                "seed_regions": _seed_regions_for_question(exam_id, question, {asset["id"]: asset for asset in exam_json["assets"]}, self.data_dir),
                "manual": _manual_question_view(exam_id, normalized, current_revision),
                "effective_assets": _effective_assets_view(
                    exam_id,
                    question,
                    normalized,
                    {asset["id"]: asset for asset in exam_json["assets"]},
                    self.data_dir,
                    self.manual_root,
                    current_revision,
                ),
            },
            "counts": manual_doc["counts"],
            "summary": self.build_exam_summary(exam_id, exam_json, audit_json, manual_doc),
        }

    def ensure_page_cache(self, exam_id: str, exam_json: dict[str, Any]) -> dict[int, dict[str, Any]]:
        cache_dir = self.page_cache_dir(exam_id)
        cache_dir.mkdir(parents=True, exist_ok=True)
        source_pdf_path = Path(exam_json["source_pdf"])
        source_pdf_mtime = source_pdf_path.stat().st_mtime_ns
        page_lookup: dict[int, dict[str, Any]] = {}

        doc = fitz.open(source_pdf_path)
        try:
            page_numbers = sorted({int(question["source"]["page"]) for question in exam_json["questions"]})
            for page_number in page_numbers:
                page = doc[page_number - 1]
                cache_path = cache_dir / f"page-{page_number}.png"
                if (
                    not cache_path.exists()
                    or cache_path.stat().st_mtime_ns < source_pdf_mtime
                ):
                    page.get_pixmap(matrix=fitz.Matrix(PAGE_CACHE_SCALE, PAGE_CACHE_SCALE), alpha=False).save(
                        cache_path.as_posix()
                    )
                page_lookup[page_number] = {
                    "number": page_number,
                    "image_url": f"/review-files/page-cache/{exam_id}/page-{page_number}.png",
                    "path": cache_path.as_posix(),
                    "pdf_width": round(page.rect.width, 2),
                    "pdf_height": round(page.rect.height, 2),
                    "pixel_width": int(round(page.rect.width * PAGE_CACHE_SCALE)),
                    "pixel_height": int(round(page.rect.height * PAGE_CACHE_SCALE)),
                }
        finally:
            doc.close()

        return page_lookup

    def _normalize_and_export_payload(
        self,
        exam_id: str,
        question_number: int,
        payload: CropQuestionUpdate,
        exam_json: dict[str, Any],
        audit_json: dict[str, Any],
    ) -> dict[str, Any]:
        status = str(payload.status or "").strip()
        if status not in MANUAL_STATUS_SET:
            raise HTTPException(status_code=422, detail=f"Unsupported crop review status '{status}'.")

        option_regions_input = {label: list(payload.option_regions.get(label, [])) for label in OPTION_LABELS}
        unknown_labels = sorted(set(payload.option_regions.keys()) - OPTION_LABEL_SET)
        if unknown_labels:
            raise HTTPException(status_code=422, detail=f"Unsupported option labels: {', '.join(unknown_labels)}.")

        if status == "completed" and set(payload.option_regions.keys()) != OPTION_LABEL_SET:
            raise HTTPException(status_code=422, detail="completed questions must provide a full A-E option_regions snapshot.")

        doc = fitz.open(exam_json["source_pdf"])
        try:
            stem_regions = _normalize_region_payloads(payload.stem_regions, doc)
            option_regions = {
                label: _normalize_region_payloads(option_regions_input[label], doc)
                for label in OPTION_LABELS
            }
            if status == "confirmed_no_visual":
                if stem_regions or any(option_regions[label] for label in OPTION_LABELS):
                    raise HTTPException(
                        status_code=422,
                        detail="confirmed_no_visual questions must save empty arrays for stem_regions and A-E option_regions.",
                    )
            if status == "completed":
                if not stem_regions and not any(option_regions[label] for label in OPTION_LABELS):
                    raise HTTPException(
                        status_code=422,
                        detail="completed questions must include at least one region, or use confirmed_no_visual.",
                    )

            resolved_exports = self._export_regions(exam_id, question_number, stem_regions, option_regions, doc)
        finally:
            doc.close()

        return {
            "status": status,
            "stem_regions": stem_regions,
            "option_regions": option_regions,
            "resolved_exports": resolved_exports,
        }

    def _export_regions(
        self,
        exam_id: str,
        question_number: int,
        stem_regions: list[dict[str, Any]],
        option_regions: dict[str, list[dict[str, Any]]],
        doc: fitz.Document,
    ) -> dict[str, Any]:
        assets_dir = self.manual_assets_dir(exam_id)
        assets_dir.mkdir(parents=True, exist_ok=True)
        self._clear_question_exports(exam_id, question_number)

        stem_exports = [
            self._export_single_region(doc, exam_id, question_number, "stem", None, index, region)
            for index, region in enumerate(stem_regions, start=1)
        ]
        option_exports = {
            label: [
                self._export_single_region(doc, exam_id, question_number, "option", label, index, region)
                for index, region in enumerate(option_regions[label], start=1)
            ]
            for label in OPTION_LABELS
        }
        return {"stem": stem_exports, "options": option_exports}

    def _export_single_region(
        self,
        doc: fitz.Document,
        exam_id: str,
        question_number: int,
        slot_kind: str,
        option_label: str | None,
        index: int,
        region: dict[str, Any],
    ) -> dict[str, Any]:
        page = doc[region["page"] - 1]
        bbox = fitz.Rect(region["bbox"])
        asset_id = (
            f"q{question_number:02d}_stem_{index:02d}"
            if slot_kind == "stem"
            else f"q{question_number:02d}_option_{option_label}_{index:02d}"
        )
        relative_path = Path(exam_id) / "assets" / f"{asset_id}.png"
        absolute_path = self.manual_root / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(matrix=fitz.Matrix(EXPORT_SCALE, EXPORT_SCALE), clip=bbox, alpha=False).save(absolute_path.as_posix())
        return {
            "slot": "stem" if slot_kind == "stem" else f"option:{option_label}",
            "asset_id": asset_id,
            "page": region["page"],
            "bbox": round_rect(bbox),
            "order": index,
            "seed_asset_id": region.get("seed_asset_id"),
            "path": relative_path.as_posix(),
            "absolute_path": absolute_path.as_posix(),
        }

    def _clear_question_exports(self, exam_id: str, question_number: int) -> None:
        assets_dir = self.manual_assets_dir(exam_id)
        if not assets_dir.exists():
            return
        prefixes = [f"q{question_number:02d}_stem_", f"q{question_number:02d}_option_"]
        for path in assets_dir.glob(f"q{question_number:02d}_*"):
            if any(path.name.startswith(prefix) for prefix in prefixes):
                path.unlink(missing_ok=True)


def crop_review_shell(view: str, exam_id: str | None) -> str:
    bootstrap = json.dumps({"view": view, "examId": exam_id}, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>图形人工框选工作台</title>
  <link rel="stylesheet" href="/review-static/crop_review.css" />
</head>
<body>
  <div id="app"></div>
  <script id="crop-review-bootstrap" type="application/json">{bootstrap}</script>
  <script type="module" src="/review-static/crop_review.js"></script>
</body>
</html>
"""


def _crop_review_schema() -> dict[str, Any]:
    return {
        "statuses": [{"value": status, "label": MANUAL_STATUS_LABELS[status]} for status in MANUAL_STATUSES],
        "slots": [{"value": "stem", "label": "题干图"}]
        + [{"value": f"option:{label}", "label": f"选项 {label}"} for label in OPTION_LABELS],
        "option_labels": list(OPTION_LABELS),
    }


def _blank_option_regions() -> dict[str, list[dict[str, Any]]]:
    return {label: [] for label in OPTION_LABELS}


def _blank_resolved_exports() -> dict[str, Any]:
    return {"stem": [], "options": {label: [] for label in OPTION_LABELS}}


def _blank_manual_question() -> dict[str, Any]:
    return {
        "status": "pending",
        "stem_regions": [],
        "option_regions": _blank_option_regions(),
        "resolved_exports": _blank_resolved_exports(),
        "updated_at": None,
        "source_revision": None,
    }


def _merge_manual_question(existing_question: Any) -> dict[str, Any]:
    if not isinstance(existing_question, dict):
        return _blank_manual_question()

    status = str(existing_question.get("status") or "").strip()
    if status not in MANUAL_STATUS_SET:
        status = "pending"
    stem_regions = _normalize_stored_regions(existing_question.get("stem_regions"))
    option_regions = {
        label: _normalize_stored_regions((existing_question.get("option_regions") or {}).get(label))
        for label in OPTION_LABELS
    }
    resolved_exports = _normalize_stored_exports(existing_question.get("resolved_exports"))
    updated_at = existing_question.get("updated_at")
    source_revision = _normalize_source_revision(existing_question.get("source_revision"))

    if status == "confirmed_no_visual":
        stem_regions = []
        option_regions = _blank_option_regions()
        resolved_exports = _blank_resolved_exports()

    return {
        "status": status,
        "stem_regions": stem_regions,
        "option_regions": option_regions,
        "resolved_exports": resolved_exports,
        "updated_at": updated_at,
        "source_revision": source_revision,
    }


def _normalize_stored_regions(raw_regions: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_regions, list):
        return []
    normalized: list[dict[str, Any]] = []
    for index, region in enumerate(raw_regions, start=1):
        if not isinstance(region, dict):
            continue
        try:
            page = int(region.get("page"))
        except (TypeError, ValueError):
            continue
        bbox = region.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        rect = fitz.Rect(bbox)
        if rect.is_empty or rect.width <= 0 or rect.height <= 0:
            continue
        normalized.append(
            {
                "page": page,
                "bbox": round_rect(rect),
                "order": int(region.get("order") or index),
                "seed_asset_id": _clean_optional_string(region.get("seed_asset_id")),
            }
        )
    normalized.sort(key=lambda item: (item["order"], item["page"], item["bbox"][1], item["bbox"][0]))
    for order, region in enumerate(normalized, start=1):
        region["order"] = order
    return normalized


def _normalize_stored_exports(raw_exports: Any) -> dict[str, Any]:
    if not isinstance(raw_exports, dict):
        return _blank_resolved_exports()
    normalized = _blank_resolved_exports()
    normalized["stem"] = _normalize_export_list(raw_exports.get("stem"))
    option_exports = raw_exports.get("options") or {}
    if isinstance(option_exports, dict):
        for label in OPTION_LABELS:
            normalized["options"][label] = _normalize_export_list(option_exports.get(label))
    return normalized


def _normalize_export_list(raw_exports: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_exports, list):
        return []
    normalized: list[dict[str, Any]] = []
    for export in raw_exports:
        if not isinstance(export, dict):
            continue
        bbox = export.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        try:
            page = int(export.get("page"))
        except (TypeError, ValueError):
            continue
        rect = fitz.Rect(bbox)
        if rect.is_empty or rect.width <= 0 or rect.height <= 0:
            continue
        normalized.append(
            {
                "slot": str(export.get("slot") or "").strip(),
                "asset_id": str(export.get("asset_id") or "").strip(),
                "page": page,
                "bbox": round_rect(rect),
                "order": int(export.get("order") or len(normalized) + 1),
                "seed_asset_id": _clean_optional_string(export.get("seed_asset_id")),
                "path": str(export.get("path") or "").strip(),
                "absolute_path": str(export.get("absolute_path") or "").strip(),
            }
        )
    normalized.sort(key=lambda item: item["order"])
    return normalized


def _normalize_source_revision(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    keys = {"exam_mtime_ns", "exam_size", "audit_mtime_ns", "audit_size"}
    return {key: value.get(key) for key in keys}


def _count_manual_statuses(question_map: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(question_map), "pending": 0, "completed": 0, "confirmed_no_visual": 0, "ready": 0}
    for question in question_map.values():
        status = question["status"]
        counts[status] += 1
        if status in READY_STATUSES:
            counts["ready"] += 1
    return counts


def _latest_manual_updated_at(question_map: dict[str, dict[str, Any]]) -> str | None:
    timestamps = [question["updated_at"] for question in question_map.values() if question.get("updated_at")]
    return max(timestamps) if timestamps else None


def _normalize_region_payloads(regions: list[CropRegionUpdate], doc: fitz.Document) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    ordered = sorted(list(regions), key=lambda item: (int(item.order), int(item.page)))
    for order, region in enumerate(ordered, start=1):
        if region.page < 1 or region.page > len(doc):
            raise HTTPException(status_code=422, detail=f"Region page {region.page} is out of bounds for this PDF.")
        rect = fitz.Rect(region.bbox)
        if rect.is_empty or rect.width <= 0 or rect.height <= 0:
            raise HTTPException(status_code=422, detail="Each region bbox must be a non-empty rectangle.")
        page_rect = doc[region.page - 1].rect
        if (
            rect.x0 < page_rect.x0
            or rect.y0 < page_rect.y0
            or rect.x1 > page_rect.x1
            or rect.y1 > page_rect.y1
        ):
            raise HTTPException(status_code=422, detail="Region bbox must stay inside the source PDF page bounds.")
        normalized.append(
            {
                "page": region.page,
                "bbox": round_rect(rect),
                "order": order,
                "seed_asset_id": _clean_optional_string(region.seed_asset_id),
            }
        )
    return normalized


def _seed_regions_for_question(
    exam_id: str,
    question: dict[str, Any],
    asset_lookup: dict[str, dict[str, Any]],
    data_dir: Path,
) -> dict[str, Any]:
    seed = {"stem": [], "options": {label: [] for label in OPTION_LABELS}}
    for index, asset_id in enumerate(question["shared_asset_refs"], start=1):
        asset = asset_lookup[asset_id]
        seed["stem"].append(_automatic_asset_region(exam_id, asset, index, data_dir))
    for choice in question["choices"]:
        for index, asset_id in enumerate(choice["asset_refs"], start=1):
            asset = asset_lookup[asset_id]
            seed["options"][choice["label"]].append(_automatic_asset_region(exam_id, asset, index, data_dir))
    return seed


def _automatic_asset_region(exam_id: str, asset: dict[str, Any], order: int, data_dir: Path) -> dict[str, Any]:
    absolute_path = (data_dir / "exams" / exam_id / asset["path"]).resolve()
    return {
        "page": asset["page"],
        "bbox": asset["bbox"],
        "order": order,
        "seed_asset_id": asset["id"],
        "asset_id": asset["id"],
        "path": asset["path"],
        "absolute_path": absolute_path.as_posix(),
        "url": f"/review-files/data/exams/{exam_id}/{asset['path']}",
    }


def _manual_question_view(exam_id: str, question: dict[str, Any], current_revision: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": question["status"],
        "status_label": MANUAL_STATUS_LABELS[question["status"]],
        "ready": question["status"] in READY_STATUSES,
        "stale": _manual_question_is_stale(question, current_revision),
        "updated_at": question.get("updated_at"),
        "source_revision": question.get("source_revision"),
        "stem_regions": question["stem_regions"],
        "option_regions": question["option_regions"],
        "resolved_exports": _resolved_exports_view(exam_id, question["resolved_exports"]),
    }


def _resolved_exports_view(exam_id: str, resolved_exports: dict[str, Any]) -> dict[str, Any]:
    return {
        "stem": [_manual_export_view(exam_id, item) for item in resolved_exports.get("stem", [])],
        "options": {
            label: [_manual_export_view(exam_id, item) for item in (resolved_exports.get("options") or {}).get(label, [])]
            for label in OPTION_LABELS
        },
    }


def _manual_export_view(_exam_id: str, export: dict[str, Any]) -> dict[str, Any]:
    path = str(export.get("path") or "").strip()
    return {
        **export,
        "url": f"/review-files/manual-crops/{path}" if path else None,
    }


def _effective_assets_view(
    exam_id: str,
    question: dict[str, Any],
    manual_question: dict[str, Any],
    asset_lookup: dict[str, dict[str, Any]],
    data_dir: Path,
    manual_root: Path,
    current_revision: dict[str, Any],
) -> dict[str, Any]:
    stale = _manual_question_is_stale(manual_question, current_revision)
    if manual_question["status"] in READY_STATUSES:
        resolved = _resolved_exports_view(exam_id, manual_question["resolved_exports"])
        return {
            "mode": "manual_override",
            "status": manual_question["status"],
            "agent_ready": True,
            "stale": stale,
            "stem": [{**item, "source": "manual"} for item in resolved["stem"]],
            "options": {
                label: [{**item, "source": "manual"} for item in resolved["options"][label]]
                for label in OPTION_LABELS
            },
        }

    return {
        "mode": "automatic",
        "status": manual_question["status"],
        "agent_ready": False,
        "stale": stale,
        "stem": [
            {
                **_automatic_asset_contract(exam_id, asset_lookup[asset_id], data_dir),
                "source": "automatic",
            }
            for asset_id in question["shared_asset_refs"]
        ],
        "options": {
            label: [
                {
                    **_automatic_asset_contract(exam_id, asset_lookup[asset_id], data_dir),
                    "source": "automatic",
                }
                for asset_id in next(choice for choice in question["choices"] if choice["label"] == label)["asset_refs"]
            ]
            for label in OPTION_LABELS
        },
    }


def _automatic_asset_contract(exam_id: str, asset: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    absolute_path = (data_dir / "exams" / exam_id / asset["path"]).resolve()
    return {
        "asset_id": asset["id"],
        "page": asset["page"],
        "bbox": asset["bbox"],
        "path": asset["path"],
        "absolute_path": absolute_path.as_posix(),
        "url": f"/review-files/data/exams/{exam_id}/{asset['path']}",
    }


def _question_is_likely_visual(question: dict[str, Any], audit_question: dict[str, Any]) -> bool:
    if question["shared_asset_refs"]:
        return True
    if any(choice["asset_refs"] for choice in question["choices"]):
        return True
    visual_counts = audit_question.get("visual_counts", {})
    return bool(visual_counts.get("drawings") or visual_counts.get("images"))


def _manual_question_is_stale(question: dict[str, Any], current_revision: dict[str, Any]) -> bool:
    if question["status"] == "pending":
        return False
    return question.get("source_revision") != current_revision


def _question_hints(question: dict[str, Any], audit_question: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    if question["shared_asset_refs"]:
        hints.append(f"当前自动题干图 {len(question['shared_asset_refs'])} 个")
    option_assets = sum(len(choice["asset_refs"]) for choice in question["choices"])
    if option_assets:
        hints.append(f"当前自动选项图 {option_assets} 个")
    if audit_question.get("visual_counts", {}).get("drawings", 0):
        hints.append(f"检测到 {audit_question['visual_counts']['drawings']} 个 drawing 对象")
    if audit_question.get("visual_counts", {}).get("images", 0):
        hints.append(f"检测到 {audit_question['visual_counts']['images']} 个 image 对象")
    if audit_question.get("missing_option_assets"):
        hints.append(f"缺少选项素材: {', '.join(audit_question['missing_option_assets'])}")
    return hints


def _clean_optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _source_revision(exam_path: Path, audit_path: Path) -> dict[str, Any]:
    return {
        "exam_mtime_ns": exam_path.stat().st_mtime_ns if exam_path.exists() else None,
        "exam_size": exam_path.stat().st_size if exam_path.exists() else None,
        "audit_mtime_ns": audit_path.stat().st_mtime_ns if audit_path.exists() else None,
        "audit_size": audit_path.stat().st_size if audit_path.exists() else None,
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
