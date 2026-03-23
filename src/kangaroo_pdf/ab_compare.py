"""Build field-level A/B manifests for comparing two extraction runs (e.g. worktrees jat vs wyo)."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _exam_field_texts(exam_payload: dict[str, Any]) -> dict[str, str]:
    """Map field_id -> text as stored in exam.json (frontend-facing)."""
    out: dict[str, str] = {}
    for question in exam_payload.get("questions", []):
        num = int(question["number"])
        qid = f"q{num:02d}"
        stem = str(question.get("stem_text") or "")
        out[f"{qid}.stem"] = stem
        for choice in question.get("choices", []):
            label = str(choice.get("label") or "").strip().upper()
            if label and label in {"A", "B", "C", "D", "E"}:
                out[f"{qid}.choice.{label}"] = str(choice.get("text") or "")
    return out


def _field_metrics_from_review(review_path: Path) -> dict[str, dict[str, Any]]:
    """Per field_id: priority, review_status, page, extracted_text snippet."""
    if not review_path.exists():
        return {}
    payload = _read_json(review_path)
    out: dict[str, dict[str, Any]] = {}
    for field in payload.get("fields", []):
        fid = field.get("field_id")
        if not isinstance(fid, str):
            continue
        out[fid] = {
            "review_priority": field.get("review_priority", ""),
            "review_status": field.get("review_status", ""),
            "page": field.get("page"),
            "extracted_text": field.get("extracted_text"),
            "verified_text": field.get("verified_text"),
        }
    return out


def _mismatch_count(data_dir: Path, exam_id: str) -> int:
    audit_path = data_dir / "exams" / exam_id / "audit.json"
    if not audit_path.exists():
        return 0
    audit = _read_json(audit_path)
    return len(audit.get("answer_source", {}).get("mismatch_questions", []))


def _exam_readiness_summary(data_dir: Path, review_dir: Path, exam_id: str) -> dict[str, Any]:
    review_path = review_dir / f"{exam_id}.json"
    priorities = Counter()
    statuses = Counter()
    field_count = 0
    if review_path.exists():
        payload = _read_json(review_path)
        fields = payload.get("fields", [])
        field_count = len(fields)
        for field in fields:
            if isinstance(field, dict):
                priorities[str(field.get("review_priority", "") or "")] += 1
                statuses[str(field.get("review_status", "") or "")] += 1
    changed = int(priorities.get("changed", 0))
    suspicious = int(priorities.get("suspicious", 0))
    pending = int(statuses.get("pending", 0))
    mismatch = _mismatch_count(data_dir, exam_id)
    return {
        "exam_id": exam_id,
        "field_count": field_count,
        "changed_count": changed,
        "suspicious_count": suspicious,
        "pending_count": pending,
        "needs_review_count": int(statuses.get("needs_review", 0)),
        "mismatch_count": mismatch,
        "pass_gate": bool(changed == 0 and suspicious == 0 and pending == 0 and mismatch == 0),
    }


@dataclass(frozen=True)
class AbCompareSide:
    """One extraction run root (typically `.generated/data` + review dir)."""

    label: str
    data_dir: Path
    review_dir: Path

    def resolve(self) -> AbCompareSide:
        return AbCompareSide(
            label=self.label,
            data_dir=self.data_dir.resolve(),
            review_dir=self.review_dir.resolve(),
        )


def default_ab_compare_roots(repo_root: Path | str) -> tuple[Path, Path]:
    """Isolated output dirs under `<repo>/.generated/ab-compare/{jat,wyo}/`."""
    root = Path(repo_root).resolve()
    base = root / ".generated" / "ab-compare"
    jat = base / "jat"
    wyo = base / "wyo"
    return jat, wyo


def ab_compare_paths_for_side(repo_root: Path | str, side: str) -> tuple[Path, Path, Path, Path]:
    """Returns (data_dir, review_dir, report_dir, release_dir) for jat or wyo slot."""
    root = Path(repo_root).resolve()
    jat, wyo = default_ab_compare_roots(root)
    slot = jat if side.lower() == "jat" else wyo
    data_dir = slot / "data"
    review_dir = slot / "review-data" / "text-verification"
    report_dir = slot / "reports" / "text-diff"
    release_dir = slot / "release-data"
    return data_dir, review_dir, report_dir, release_dir


def build_ab_manifest(
    side_a: AbCompareSide,
    side_b: AbCompareSide,
    *,
    repo_root: Path | str,
    exam_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Join two runs on exam_id + field_id; include diff flags and per-exam summaries."""
    a = side_a.resolve()
    b = side_b.resolve()
    root = Path(repo_root).resolve()
    manifest_a = _read_json(a.data_dir / "manifest.json")
    manifest_b = _read_json(b.data_dir / "manifest.json")
    ids_a = [e["exam_id"] for e in manifest_a.get("exams", [])]
    ids_b = [e["exam_id"] for e in manifest_b.get("exams", [])]
    common = sorted(set(ids_a) & set(ids_b))
    if exam_ids:
        wanted = set(exam_ids)
        common = [eid for eid in common if eid in wanted]
        missing = sorted(wanted - set(common))
        if missing:
            raise ValueError(f"exam_ids not present in both runs: {missing}")

    rows: list[dict[str, Any]] = []
    exam_summaries: list[dict[str, Any]] = []

    for exam_id in common:
        path_a = a.data_dir / "exams" / exam_id / "exam.json"
        path_b = b.data_dir / "exams" / exam_id / "exam.json"
        if not path_a.exists() or not path_b.exists():
            continue
        exam_a = _read_json(path_a)
        exam_b = _read_json(path_b)
        texts_a = _exam_field_texts(exam_a)
        texts_b = _exam_field_texts(exam_b)
        metrics_a = _field_metrics_from_review(a.review_dir / f"{exam_id}.json")
        metrics_b = _field_metrics_from_review(b.review_dir / f"{exam_id}.json")

        all_keys = sorted(set(texts_a.keys()) | set(texts_b.keys()))
        summary_a = _exam_readiness_summary(a.data_dir, a.review_dir, exam_id)
        summary_b = _exam_readiness_summary(b.data_dir, b.review_dir, exam_id)
        summary_a["label"] = a.label
        summary_b["label"] = b.label
        raw_pdf = exam_a.get("source_pdf") or exam_b.get("source_pdf")
        pdf_resolved: str | None = None
        if raw_pdf:
            p = Path(str(raw_pdf))
            if p.is_absolute() and p.exists():
                pdf_resolved = p.as_posix()
            elif not p.is_absolute():
                cand = (root / p).resolve()
                if cand.exists():
                    pdf_resolved = cand.as_posix()
        exam_summaries.append(
            {
                "exam_id": exam_id,
                "side_a": summary_a,
                "side_b": summary_b,
                "source_pdf": raw_pdf,
                "source_pdf_resolved": pdf_resolved,
            }
        )

        for field_id in all_keys:
            t_a = texts_a.get(field_id, "")
            t_b = texts_b.get(field_id, "")
            ma = metrics_a.get(field_id, {})
            mb = metrics_b.get(field_id, {})
            same_raw = t_a == t_b
            same_norm = _norm_ws(t_a) == _norm_ws(t_b)
            suspicious = (ma.get("review_priority") == "suspicious") or (mb.get("review_priority") == "suspicious")
            row = {
                "exam_id": exam_id,
                "field_id": field_id,
                "text_a": t_a,
                "text_b": t_b,
                "same_raw": same_raw,
                "same_normalized": same_norm,
                "any_suspicious": suspicious,
                "page": ma.get("page") if ma.get("page") is not None else mb.get("page"),
                "side_a": {
                    "review_priority": ma.get("review_priority", ""),
                    "review_status": ma.get("review_status", ""),
                },
                "side_b": {
                    "review_priority": mb.get("review_priority", ""),
                    "review_status": mb.get("review_status", ""),
                },
            }
            rows.append(row)

    pdf_root = root / "original_pdf_data"
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": root.as_posix(),
        "original_pdf_data": pdf_root.as_posix(),
        "side_a": {"label": a.label, "data_dir": a.data_dir.as_posix(), "review_dir": a.review_dir.as_posix()},
        "side_b": {"label": b.label, "data_dir": b.data_dir.as_posix(), "review_dir": b.review_dir.as_posix()},
        "exam_ids": common,
        "exam_count": len(common),
        "field_count": len(rows),
        "diff_count": sum(1 for r in rows if not r["same_raw"]),
        "exam_summaries": exam_summaries,
        "rows": rows,
    }
