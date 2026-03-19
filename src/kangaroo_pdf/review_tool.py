from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

REVIEW_STATUSES = ("unreviewed", "passed", "failed", "follow_up")
REVIEW_STATUS_SET = set(REVIEW_STATUSES)

ISSUE_TYPES = (
    "crop_region",
    "missing_asset",
    "wrong_asset",
    "asset_order",
    "stem_text_error",
    "choice_text_error",
    "answer_key_error",
    "layout_render_error",
    "other",
)
ISSUE_TYPE_SET = set(ISSUE_TYPES)

AFFECTED_AREAS = ("reference_crop", "stem", "choices", "answer", "whole_question")
AFFECTED_AREA_SET = set(AFFECTED_AREAS)

STATUS_LABELS = {
    "unreviewed": "未审核",
    "passed": "通过",
    "failed": "不通过",
    "follow_up": "待复查",
}

ISSUE_LABELS = {
    "crop_region": "裁图区域不对",
    "missing_asset": "缺少素材",
    "wrong_asset": "素材不对",
    "asset_order": "素材顺序不对",
    "stem_text_error": "题干文本有误",
    "choice_text_error": "选项文本有误",
    "answer_key_error": "答案有误",
    "layout_render_error": "渲染布局异常",
    "other": "其他问题",
}

AFFECTED_AREA_LABELS = {
    "reference_crop": "原始裁图",
    "stem": "题干区",
    "choices": "选项区",
    "answer": "答案区",
    "whole_question": "整题",
}


class ReviewQuestionUpdate(BaseModel):
    status: str
    issue_types: list[str] = Field(default_factory=list)
    affected_areas: list[str] = Field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class ReviewRepository:
    data_dir: Path
    review_dir: Path

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "manifest.json"

    @property
    def qa_root(self) -> Path:
        return self.data_dir.parent / "reports" / "asset-qa"

    @property
    def static_root(self) -> Path:
        return Path(__file__).resolve().parent / "review_static"

    def manifest(self) -> dict[str, Any]:
        return _read_json(self.manifest_path)

    def exam_entries(self) -> list[dict[str, Any]]:
        manifest = self.manifest()
        return list(manifest.get("exams", []))

    def exam_dir(self, exam_id: str) -> Path:
        return self.data_dir / "exams" / exam_id

    def review_path(self, exam_id: str) -> Path:
        return self.review_dir / f"{exam_id}.json"

    def exam_paths(self, exam_id: str) -> tuple[Path, Path]:
        exam_dir = self.exam_dir(exam_id)
        return exam_dir / "exam.json", exam_dir / "audit.json"

    def qa_page_path(self, exam_id: str) -> Path:
        return self.qa_root / exam_id / "index.html"

    def exam_urls(self, exam_id: str) -> dict[str, str]:
        return {
            "exam_json_url": f"/review-files/data/exams/{exam_id}/exam.json",
            "audit_json_url": f"/review-files/data/exams/{exam_id}/audit.json",
            "qa_page_url": f"/review-files/qa/{exam_id}/index.html",
            "review_page_url": f"/review/{exam_id}",
        }

    def load_exam_bundle(self, exam_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        exam_path, audit_path = self.exam_paths(exam_id)
        if not exam_path.exists() or not audit_path.exists():
            raise KeyError(exam_id)
        exam_json = _read_json(exam_path)
        audit_json = _read_json(audit_path)
        review_doc = self.load_review_document(exam_id, exam_json, audit_json)
        return exam_json, audit_json, review_doc

    def load_review_document(
        self,
        exam_id: str,
        exam_json: dict[str, Any],
        audit_json: dict[str, Any],
    ) -> dict[str, Any]:
        path = self.review_path(exam_id)
        existing = _read_json(path) if path.exists() else {}
        existing_questions = existing.get("questions", {})

        merged_questions: dict[str, dict[str, Any]] = {}
        for question in exam_json["questions"]:
            key = str(question["number"])
            merged_questions[key] = _merge_review_question(existing_questions.get(key))

        review_doc = {
            "exam_id": exam_id,
            "updated_at": existing.get("updated_at"),
            "source_refs": {
                "exam_json": self.exam_paths(exam_id)[0].as_posix(),
                "audit_json": self.exam_paths(exam_id)[1].as_posix(),
                "qa_page": self.qa_page_path(exam_id).as_posix(),
                "source_pdf": exam_json.get("source_pdf"),
                "source_revision": _source_revision(self.exam_paths(exam_id)[0], self.exam_paths(exam_id)[1]),
            },
            "counts": {},
            "questions": merged_questions,
        }
        review_doc["counts"] = _count_review_statuses(review_doc["questions"])
        if not review_doc["updated_at"]:
            review_doc["updated_at"] = _latest_reviewed_at(review_doc["questions"])
        return review_doc

    def save_question_review(
        self,
        exam_id: str,
        question_number: int,
        payload: ReviewQuestionUpdate,
    ) -> dict[str, Any]:
        exam_json, audit_json, review_doc = self.load_exam_bundle(exam_id)
        valid_numbers = {question["number"] for question in exam_json["questions"]}
        if question_number not in valid_numbers:
            raise HTTPException(status_code=404, detail=f"Question {question_number} was not found.")

        normalized = _normalize_review_payload(payload)
        saved_at = _utc_now_iso()
        normalized["reviewed_at"] = None if normalized["status"] == "unreviewed" else saved_at
        review_doc["questions"][str(question_number)] = normalized
        review_doc["counts"] = _count_review_statuses(review_doc["questions"])
        review_doc["updated_at"] = saved_at
        _write_json(self.review_path(exam_id), review_doc)
        return {
            "question": review_doc["questions"][str(question_number)],
            "counts": review_doc["counts"],
            "summary": self.build_exam_summary(exam_id, exam_json, audit_json, review_doc),
        }

    def build_exam_summary(
        self,
        exam_id: str,
        exam_json: dict[str, Any],
        audit_json: dict[str, Any],
        review_doc: dict[str, Any],
    ) -> dict[str, Any]:
        counts = review_doc["counts"]
        first_unreviewed = _first_question_by_status(review_doc["questions"], "unreviewed")
        latest_reviewed_number = _latest_reviewed_question(review_doc["questions"])
        latest_reviewed_at = _latest_reviewed_at(review_doc["questions"])
        failure_numbers = _question_numbers_by_status(review_doc["questions"], {"failed", "follow_up"})
        urls = self.exam_urls(exam_id)
        return {
            "exam_id": exam_id,
            "family": exam_json["family"],
            "year": exam_json["year"],
            "question_count": len(exam_json["questions"]),
            "answer_count": len(exam_json.get("answer_key", {})),
            "warning_count": len(exam_json.get("warnings", [])) + len(audit_json.get("warnings", [])),
            "counts": counts,
            "progress_percent": round((counts["reviewed"] / len(exam_json["questions"])) * 100, 1)
            if exam_json["questions"]
            else 0.0,
            "updated_at": review_doc.get("updated_at"),
            "last_reviewed_at": latest_reviewed_at,
            "last_reviewed_question": latest_reviewed_number,
            "continue_question": latest_reviewed_number or first_unreviewed or 1,
            "first_unreviewed_question": first_unreviewed,
            "first_failure_question": failure_numbers[0] if failure_numbers else None,
            "review_url": urls["review_page_url"],
            "continue_url": f"{urls['review_page_url']}?question={latest_reviewed_number or first_unreviewed or 1}",
            "first_unreviewed_url": (
                f"{urls['review_page_url']}?question={first_unreviewed}" if first_unreviewed else urls["review_page_url"]
            ),
            "failures_url": "/review/queue/failures",
            "qa_page_url": urls["qa_page_url"],
            "exam_json_url": urls["exam_json_url"],
            "audit_json_url": urls["audit_json_url"],
        }

    def list_exam_summaries(self) -> dict[str, Any]:
        manifest = self.manifest()
        summaries: list[dict[str, Any]] = []
        total_counts = {"total_questions": 0, "reviewed": 0, "unreviewed": 0, "passed": 0, "failed": 0, "follow_up": 0}

        for entry in self.exam_entries():
            exam_id = entry["exam_id"]
            exam_json, audit_json, review_doc = self.load_exam_bundle(exam_id)
            summary = self.build_exam_summary(exam_id, exam_json, audit_json, review_doc)
            summaries.append(summary)
            total_counts["total_questions"] += summary["question_count"]
            total_counts["reviewed"] += summary["counts"]["reviewed"]
            total_counts["unreviewed"] += summary["counts"]["unreviewed"]
            total_counts["passed"] += summary["counts"]["passed"]
            total_counts["failed"] += summary["counts"]["failed"]
            total_counts["follow_up"] += summary["counts"]["follow_up"]

        total_counts["exams"] = len(summaries)
        total_counts["progress_percent"] = round(
            (total_counts["reviewed"] / total_counts["total_questions"]) * 100, 1
        ) if total_counts["total_questions"] else 0.0
        return {
            "generated_at": manifest.get("generated_at"),
            "schema": _review_schema(),
            "counts": total_counts,
            "exams": summaries,
        }

    def exam_detail(self, exam_id: str) -> dict[str, Any]:
        exam_json, audit_json, review_doc = self.load_exam_bundle(exam_id)
        asset_lookup = {asset["id"]: asset for asset in exam_json["assets"]}
        audit_lookup = {question["number"]: question for question in audit_json["questions"]}
        question_views: list[dict[str, Any]] = []

        for question in exam_json["questions"]:
            audit_question = audit_lookup[question["number"]]
            question_views.append(
                {
                    "number": question["number"],
                    "id": question["id"],
                    "part": question["part"],
                    "points": question["points"],
                    "answer": question.get("answer"),
                    "stem_text": question.get("stem_text", ""),
                    "choices": [_choice_view(exam_id, choice, asset_lookup) for choice in question["choices"]],
                    "shared_assets": [_asset_view(exam_id, asset_lookup[asset_id]) for asset_id in question["shared_asset_refs"]],
                    "source": question["source"],
                    "audit": audit_question,
                    "review": review_doc["questions"][str(question["number"])],
                    "reference_image_url": (
                        f"/review-files/qa/{exam_id}/{audit_question['qa_reference_path']}"
                        if audit_question.get("qa_reference_path")
                        else None
                    ),
                    "qa_anchor_url": f"/review-files/qa/{exam_id}/index.html#q{question['number']:02d}",
                    "question_url": f"/review/{exam_id}?question={question['number']}",
                    "system_hints": _question_hints(question, audit_question),
                }
            )

        summary = self.build_exam_summary(exam_id, exam_json, audit_json, review_doc)
        summary["continue_question"] = summary["continue_question"] or 1
        return {
            "schema": _review_schema(),
            "meta": {
                **summary,
                **self.exam_urls(exam_id),
            },
            "exam": exam_json,
            "audit": audit_json,
            "review": review_doc,
            "question_views": question_views,
        }

    def repair_backlog(self) -> dict[str, Any]:
        exams_payload: list[dict[str, Any]] = []
        issue_counts: dict[str, int] = {issue_type: 0 for issue_type in ISSUE_TYPES}
        total_items = 0

        for entry in self.exam_entries():
            exam_id = entry["exam_id"]
            detail = self.exam_detail(exam_id)
            backlog_items: list[dict[str, Any]] = []
            for question in detail["question_views"]:
                status = question["review"]["status"]
                if status not in {"failed", "follow_up"}:
                    continue
                for issue_type in question["review"]["issue_types"]:
                    issue_counts[issue_type] += 1
                backlog_items.append(
                    {
                        "exam_id": exam_id,
                        "question_number": question["number"],
                        "status": status,
                        "status_label": STATUS_LABELS[status],
                        "issue_types": question["review"]["issue_types"],
                        "affected_areas": question["review"]["affected_areas"],
                        "note": question["review"]["note"],
                        "reviewed_at": question["review"]["reviewed_at"],
                        "reference_bbox": question["audit"]["reference_bbox"],
                        "text_bbox": question["audit"]["text_bbox"],
                        "page": question["source"]["page"],
                        "reference_image_url": question["reference_image_url"],
                        "question_url": question["question_url"],
                        "qa_anchor_url": question["qa_anchor_url"],
                        "answer": question["answer"],
                        "shared_asset_ids": [asset["id"] for asset in question["shared_assets"]],
                        "option_asset_ids": {
                            choice["label"]: [asset["id"] for asset in choice["asset_views"]]
                            for choice in question["choices"]
                            if choice["asset_views"]
                        },
                        "system_hints": question["system_hints"],
                    }
                )
            if backlog_items:
                total_items += len(backlog_items)
                exams_payload.append(
                    {
                        "exam_id": exam_id,
                        "question_count": detail["meta"]["question_count"],
                        "counts": detail["meta"]["counts"],
                        "qa_page_url": detail["meta"]["qa_page_url"],
                        "review_url": detail["meta"]["review_url"],
                        "items": backlog_items,
                    }
                )

        return {
            "generated_at": _utc_now_iso(),
            "schema": _review_schema(),
            "total_items": total_items,
            "issue_type_counts": [
                {"value": issue_type, "label": ISSUE_LABELS[issue_type], "count": issue_counts[issue_type]}
                for issue_type in ISSUE_TYPES
            ],
            "exams": exams_payload,
        }


def create_review_app(data_dir: Path | str, review_dir: Path | str) -> FastAPI:
    repository = ReviewRepository(Path(data_dir).resolve(), Path(review_dir).resolve())
    repository.review_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Math Exam Review Tool")
    app.mount("/review-static", StaticFiles(directory=str(repository.static_root)), name="review-static")
    app.mount("/review-files/data", StaticFiles(directory=str(repository.data_dir)), name="review-data-files")
    app.mount(
        "/review-files/qa",
        StaticFiles(directory=str(repository.qa_root), check_dir=False),
        name="review-qa-files",
    )

    @app.get("/", include_in_schema=False)
    def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/review")

    @app.get("/api/review/exams")
    def api_review_exams() -> dict[str, Any]:
        return repository.list_exam_summaries()

    @app.get("/api/review/exams/{exam_id}")
    def api_review_exam_detail(exam_id: str) -> dict[str, Any]:
        try:
            return repository.exam_detail(exam_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=f"Exam '{exam_id}' was not found.") from error

    @app.put("/api/review/exams/{exam_id}/questions/{question_number}")
    def api_update_review_question(
        exam_id: str,
        question_number: int,
        payload: ReviewQuestionUpdate,
    ) -> dict[str, Any]:
        try:
            return repository.save_question_review(exam_id, question_number, payload)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=f"Exam '{exam_id}' was not found.") from error

    @app.get("/api/review/repair-backlog")
    def api_review_repair_backlog() -> dict[str, Any]:
        return repository.repair_backlog()

    @app.get("/review", response_class=HTMLResponse)
    def review_dashboard() -> HTMLResponse:
        return HTMLResponse(_review_shell(view="overview", exam_id=None))

    @app.get("/review/queue/failures", response_class=HTMLResponse)
    def review_failures() -> HTMLResponse:
        return HTMLResponse(_review_shell(view="queue", exam_id=None))

    @app.get("/review/{exam_id}", response_class=HTMLResponse)
    def review_exam_page(exam_id: str) -> HTMLResponse:
        try:
            repository.load_exam_bundle(exam_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=f"Exam '{exam_id}' was not found.") from error
        return HTMLResponse(_review_shell(view="exam", exam_id=exam_id))

    return app


def _choice_view(exam_id: str, choice: dict[str, Any], asset_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "label": choice["label"],
        "text": choice.get("text") or "",
        "asset_views": [_asset_view(exam_id, asset_lookup[asset_id]) for asset_id in choice["asset_refs"]],
    }


def _asset_view(exam_id: str, asset: dict[str, Any]) -> dict[str, Any]:
    return {
        **asset,
        "url": f"/review-files/data/exams/{exam_id}/{asset['path']}",
    }


def _question_hints(question: dict[str, Any], audit_question: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    if audit_question.get("missing_option_assets"):
        hints.append(f"缺少选项素材: {', '.join(audit_question['missing_option_assets'])}")
    if audit_question.get("visual_counts", {}).get("drawings", 0):
        hints.append(f"检测到 {audit_question['visual_counts']['drawings']} 个 drawing 对象")
    if audit_question.get("visual_counts", {}).get("images", 0):
        hints.append(f"检测到 {audit_question['visual_counts']['images']} 个 image 对象")
    if question.get("source", {}).get("confidence") is not None:
        hints.append(f"抽取置信度 {question['source']['confidence']}")
    if audit_question.get("answer_confidence") is not None:
        hints.append(f"答案置信度 {audit_question['answer_confidence']}")
    return hints


def _merge_review_question(existing_question: Any) -> dict[str, Any]:
    if not isinstance(existing_question, dict):
        return _blank_review_question()

    status = existing_question.get("status")
    if status not in REVIEW_STATUS_SET:
        return _blank_review_question()

    issue_types = _normalize_stored_tokens(existing_question.get("issue_types", []), ISSUE_TYPE_SET)
    affected_areas = _normalize_stored_tokens(existing_question.get("affected_areas", []), AFFECTED_AREA_SET)
    note = str(existing_question.get("note", "") or "").strip()
    reviewed_at = existing_question.get("reviewed_at")
    if status in {"failed", "follow_up"} and not issue_types:
        return _blank_review_question()
    if status == "unreviewed":
        return _blank_review_question()
    if status == "passed":
        issue_types = []
        affected_areas = []
    return {
        "status": status,
        "issue_types": issue_types,
        "affected_areas": affected_areas,
        "note": note,
        "reviewed_at": reviewed_at,
    }


def _normalize_review_payload(payload: ReviewQuestionUpdate) -> dict[str, Any]:
    status = str(payload.status or "").strip()
    if status not in REVIEW_STATUS_SET:
        raise HTTPException(status_code=422, detail=f"Unsupported status '{status}'.")

    issue_types = _normalize_tokens(payload.issue_types, ISSUE_TYPE_SET)
    affected_areas = _normalize_tokens(payload.affected_areas, AFFECTED_AREA_SET)
    note = str(payload.note or "").strip()

    if status in {"failed", "follow_up"} and not issue_types:
        raise HTTPException(status_code=422, detail="issue_types are required for failed/follow_up questions.")
    if status == "unreviewed":
        return _blank_review_question()
    if status == "passed":
        issue_types = []
        affected_areas = []

    return {
        "status": status,
        "issue_types": issue_types,
        "affected_areas": affected_areas,
        "note": note,
        "reviewed_at": None,
    }


def _normalize_tokens(values: Any, allowed_values: set[str]) -> list[str]:
    if not isinstance(values, list):
        raise HTTPException(status_code=422, detail="Expected a list field in the review payload.")
    seen: set[str] = set()
    normalized: list[str] = []
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value:
            continue
        if value not in allowed_values:
            raise HTTPException(status_code=422, detail=f"Unsupported review token '{value}'.")
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _normalize_stored_tokens(values: Any, allowed_values: set[str]) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value or value not in allowed_values or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _count_review_statuses(question_map: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(question_map), "reviewed": 0, "unreviewed": 0, "passed": 0, "failed": 0, "follow_up": 0}
    for question in question_map.values():
        status = question["status"]
        counts[status] += 1
        if status != "unreviewed":
            counts["reviewed"] += 1
    return counts


def _latest_reviewed_at(question_map: dict[str, dict[str, Any]]) -> str | None:
    timestamps = [question["reviewed_at"] for question in question_map.values() if question.get("reviewed_at")]
    return max(timestamps) if timestamps else None


def _latest_reviewed_question(question_map: dict[str, dict[str, Any]]) -> int | None:
    candidates = [
        (question["reviewed_at"], int(number))
        for number, question in question_map.items()
        if question.get("reviewed_at")
    ]
    if not candidates:
        return None
    return max(candidates)[1]


def _first_question_by_status(question_map: dict[str, dict[str, Any]], target_status: str) -> int | None:
    question_numbers = _question_numbers_by_status(question_map, {target_status})
    return question_numbers[0] if question_numbers else None


def _question_numbers_by_status(question_map: dict[str, dict[str, Any]], statuses: set[str]) -> list[int]:
    return sorted(int(number) for number, question in question_map.items() if question["status"] in statuses)


def _blank_review_question() -> dict[str, Any]:
    return {
        "status": "unreviewed",
        "issue_types": [],
        "affected_areas": [],
        "note": "",
        "reviewed_at": None,
    }


def _source_revision(exam_path: Path, audit_path: Path) -> dict[str, Any]:
    return {
        "exam_mtime_ns": exam_path.stat().st_mtime_ns if exam_path.exists() else None,
        "exam_size": exam_path.stat().st_size if exam_path.exists() else None,
        "audit_mtime_ns": audit_path.stat().st_mtime_ns if audit_path.exists() else None,
        "audit_size": audit_path.stat().st_size if audit_path.exists() else None,
    }


def _review_schema() -> dict[str, Any]:
    return {
        "statuses": [{"value": status, "label": STATUS_LABELS[status]} for status in REVIEW_STATUSES],
        "issue_types": [{"value": issue_type, "label": ISSUE_LABELS[issue_type]} for issue_type in ISSUE_TYPES],
        "affected_areas": [
            {"value": affected_area, "label": AFFECTED_AREA_LABELS[affected_area]}
            for affected_area in AFFECTED_AREAS
        ],
    }


def _review_shell(view: str, exam_id: str | None) -> str:
    bootstrap = json.dumps({"view": view, "examId": exam_id}, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>模拟考试人工审核工作台</title>
  <link rel="stylesheet" href="/review-static/review.css" />
</head>
<body>
  <div id="app"></div>
  <script id="review-bootstrap" type="application/json">{bootstrap}</script>
  <script type="module" src="/review-static/review.js"></script>
</body>
</html>
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
