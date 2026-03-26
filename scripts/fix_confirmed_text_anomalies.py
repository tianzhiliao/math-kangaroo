#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "release-data" / "manifest.json"
FINDINGS_PATH = ROOT / ".generated" / "reports" / "text-anomaly-scan" / "findings.json"
REPORT_PATH = ROOT / ".generated" / "reports" / "text-anomaly-scan" / "fix-results.json"
REPORT_MD_PATH = ROOT / ".generated" / "reports" / "text-anomaly-scan" / "fix-results.md"

POLLUTION_RE = re.compile(
    r"(?:"
    r"\bPART\s+[A-Z]\b.*|"
    r"\b\d+\s*Point Questions?\b.*|"
    r"\b\d*\s*points?\s+problems?\b.*|"
    r"\bName:\b.*|\bSchool:\b.*|\bClass:\b.*|"
    r"\bcopyright\b.*|\bAll rights reserved\b.*|"
    r"\bMath Kangaroo\b.*|\bPage\s+\d+\b.*"
    r")",
    re.IGNORECASE,
)
SYMBOL_NOISE_RE = re.compile(r"(?:[°{}\\@|~]){2,}")
LABEL_RUN_RE = re.compile(r"\b(?:[A-E]\s+){3,}[A-E]\b")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class FixLog:
    exam_id: str
    question_number: int
    field: str
    before: str
    after: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "exam_id": self.exam_id,
            "question_number": self.question_number,
            "field": self.field,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
        }


def _collapse(text: str) -> str:
    return WHITESPACE_RE.sub(" ", (text or "").strip()).strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _clean_generic_stem(text: str) -> str:
    cleaned = text or ""
    cleaned = POLLUTION_RE.sub("", cleaned)
    cleaned = re.sub(r"^\s*Thi\s+t\s+i.*?\b\d+\.\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bA\s+B\s+C\s+D\s+E\b.*$", "", cleaned)
    cleaned = LABEL_RUN_RE.sub("", cleaned)
    cleaned = SYMBOL_NOISE_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+[.,;:!?]", lambda m: m.group(0).strip(), cleaned)
    return _collapse(cleaned)


def _clean_generic_choice(text: str) -> str:
    cleaned = text or ""
    cleaned = POLLUTION_RE.sub("", cleaned)
    cleaned = LABEL_RUN_RE.sub("", cleaned)
    cleaned = SYMBOL_NOISE_RE.sub(" ", cleaned)
    cleaned = _collapse(cleaned)
    if re.fullmatch(r"\d+\s*-\s*", cleaned):
        return re.sub(r"\D", "", cleaned)
    if re.fullmatch(r"E(?:\s+E)+", cleaned):
        return "E"
    if cleaned.lower().startswith("e this material may be reproduced"):
        return "E"
    return cleaned


def _apply_targeted_stem_overrides(exam_id: str, qn: int, text: str) -> tuple[str, str | None]:
    current = text
    # Confirmed high-noise stem can be safely reconstructed from surviving readable fragments.
    if exam_id == "felix-austria-2015" and qn == 5:
        return (
            "Florian has 10 equally long metal strips with equally many holes. "
            "He bolts the metal strips together in pairs. Now he has five long strips "
            "(see the diagram). Which of the long strips is the shortest?",
            "manual_reconstruction_from_pdf_context",
        )
    if exam_id == "felix-austria-2015" and qn == 7:
        cleaned = re.sub(r"\?\s+.*$", "?", current)
        return (_collapse(cleaned), "trim_trailing_garble_after_question_mark")
    if exam_id == "felix-brazil-2021" and qn == 13:
        cleaned = re.sub(r"(\bcode\s+\d+(?:\s+\d+){4,})\s+(?:[A-E]\s+){3,}[A-E]\s*\.", r"\1.", current)
        cleaned = _clean_generic_stem(cleaned)
        return (cleaned, "remove_option_label_run_inside_stem")
    if exam_id == "canada-gr0102e-2021" and qn == 3:
        return (
            "Four identical pieces of paper are placed as shown. Michael wants to make a hole "
            "that goes through all four pieces of paper. Where should Michael make the hole?",
            "restore_lost_tail_question_clause",
        )
    return (current, None)


def _load_exam_payloads(manifest: dict[str, Any]) -> dict[str, tuple[Path, dict[str, Any]]]:
    root = MANIFEST_PATH.parent
    out: dict[str, tuple[Path, dict[str, Any]]] = {}
    for entry in manifest["exams"]:
        exam_path = root / entry["path"]
        out[entry["exam_id"]] = (exam_path, _read_json(exam_path))
    return out


def _fix_targeted_findings(
    findings: list[dict[str, Any]],
    exams: dict[str, tuple[Path, dict[str, Any]]],
) -> tuple[list[FixLog], list[dict[str, Any]]]:
    logs: list[FixLog] = []
    unresolved: list[dict[str, Any]] = []
    for item in findings:
        exam_id = item["exam_id"]
        qn = int(item["question_number"])
        field = item["field"]
        choice_label = item.get("choice_label")
        _, payload = exams[exam_id]
        question = next((q for q in payload["questions"] if int(q["number"]) == qn), None)
        if not question:
            unresolved.append({**item, "reason": "question_not_found"})
            continue
        if field == "stem_text":
            before = question.get("stem_text", "")
            after = _clean_generic_stem(before)
            override, reason = _apply_targeted_stem_overrides(exam_id, qn, after)
            if reason:
                after = override
                fix_reason = reason
            else:
                fix_reason = "generic_stem_cleanup"
            if after and after != before:
                question["stem_text"] = after
                logs.append(FixLog(exam_id, qn, "stem_text", before, after, fix_reason))
            elif not after:
                unresolved.append({**item, "reason": "stem_became_empty_after_cleanup"})
        elif field == "choice_text" and choice_label:
            choice = next((c for c in question["choices"] if c["label"] == choice_label), None)
            if not choice:
                unresolved.append({**item, "reason": "choice_not_found"})
                continue
            before = choice.get("text", "")
            after = _clean_generic_choice(before)
            if choice.get("asset_refs") and item["issue_type"] in {"option_pollution", "garbled_symbols"}:
                # For image-backed options, leaked text should be removed.
                after = ""
            if after != before:
                choice["text"] = after
                logs.append(
                    FixLog(
                        exam_id,
                        qn,
                        f"choice_text[{choice_label}]",
                        before,
                        after,
                        "targeted_choice_cleanup",
                    )
                )
            if not after and not choice.get("asset_refs"):
                unresolved.append({**item, "reason": "non_asset_choice_empty_after_cleanup"})
    return logs, unresolved


def _fix_all_e_pollution(exams: dict[str, tuple[Path, dict[str, Any]]]) -> tuple[list[FixLog], list[dict[str, Any]]]:
    logs: list[FixLog] = []
    unresolved: list[dict[str, Any]] = []
    for exam_id, (_path, payload) in exams.items():
        for q in payload["questions"]:
            qn = int(q["number"])
            choice_e = next((c for c in q["choices"] if c["label"] == "E"), None)
            if not choice_e:
                continue
            before = choice_e.get("text", "")
            if not before:
                continue
            has_pollution = bool(POLLUTION_RE.search(before))
            has_known_residual = bool(
                re.fullmatch(r"\d+\s*-\s*", _collapse(before))
                or re.fullmatch(r"E(?:\s+E)+", _collapse(before))
                or _collapse(before).lower().startswith("e this material may be reproduced")
            )
            if not has_pollution and not has_known_residual:
                continue
            after = _clean_generic_choice(before)
            if choice_e.get("asset_refs"):
                after = ""
            if after != before:
                choice_e["text"] = after
                logs.append(
                    FixLog(
                        exam_id,
                        qn,
                        "choice_text[E]",
                        before,
                        after,
                        "global_e_option_pollution_cleanup",
                    )
                )
            if not after and not choice_e.get("asset_refs"):
                unresolved.append(
                    {
                        "exam_id": exam_id,
                        "question_number": qn,
                        "field": "choice_text[E]",
                        "reason": "non_asset_e_choice_empty_after_cleanup",
                        "before": before,
                    }
                )
    return logs, unresolved


def _apply_known_hotfixes(exams: dict[str, tuple[Path, dict[str, Any]]]) -> list[FixLog]:
    logs: list[FixLog] = []
    # canada-gr0102e-2021 q03 stem lost tail clause in generic cleanup.
    exam = exams.get("canada-gr0102e-2021")
    if exam:
        _, payload = exam
        q3 = next((q for q in payload["questions"] if int(q["number"]) == 3), None)
        if q3:
            before = q3.get("stem_text", "")
            after = (
                "Four identical pieces of paper are placed as shown. Michael wants to make a hole "
                "that goes through all four pieces of paper. Where should Michael make the hole?"
            )
            if before != after:
                q3["stem_text"] = after
                logs.append(
                    FixLog(
                        "canada-gr0102e-2021",
                        3,
                        "stem_text",
                        before,
                        after,
                        "known_hotfix_restore_question_clause",
                    )
                )
    return logs


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Text Fix Results")
    lines.append("")
    lines.append(f"- generated_at: `{payload['generated_at']}`")
    lines.append(f"- targeted_fixes: `{payload['summary']['targeted_fix_count']}`")
    lines.append(f"- global_e_fixes: `{payload['summary']['global_e_fix_count']}`")
    lines.append(f"- unresolved: `{payload['summary']['unresolved_count']}`")
    lines.append("")
    lines.append("## Applied Fixes")
    lines.append("")
    lines.append("| exam_id | q | field | reason | before | after |")
    lines.append("|---|---:|---|---|---|---|")
    for item in payload["applied_fixes"]:
        b = _collapse(item["before"]).replace("|", "\\|")
        a = _collapse(item["after"]).replace("|", "\\|")
        lines.append(
            f"| {item['exam_id']} | {item['question_number']} | {item['field']} | {item['reason']} | {b} | {a} |"
        )
    lines.append("")
    lines.append("## Unresolved")
    lines.append("")
    if payload["unresolved"]:
        lines.append("| exam_id | q | field | reason |")
        lines.append("|---|---:|---|---|")
        for item in payload["unresolved"]:
            lines.append(
                f"| {item.get('exam_id')} | {item.get('question_number')} | {item.get('field')} | {item.get('reason')} |"
            )
    else:
        lines.append("None.")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply confirmed text anomaly fixes to release-data exam JSON files.")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--findings", default=str(FINDINGS_PATH))
    parser.add_argument("--report-json", default=str(REPORT_PATH))
    parser.add_argument("--report-md", default=str(REPORT_MD_PATH))
    args = parser.parse_args()

    manifest = _read_json(Path(args.manifest))
    findings_payload = _read_json(Path(args.findings))
    exams = _load_exam_payloads(manifest)
    findings = list(findings_payload.get("findings", []))

    targeted_logs, targeted_unresolved = _fix_targeted_findings(findings, exams)
    global_logs, global_unresolved = _fix_all_e_pollution(exams)
    hotfix_logs = _apply_known_hotfixes(exams)

    for exam_id, (path, payload) in exams.items():
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    applied = [*targeted_logs, *global_logs, *hotfix_logs]
    unresolved = [*targeted_unresolved, *global_unresolved]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "targeted_fix_count": len(targeted_logs),
            "global_e_fix_count": len(global_logs),
            "known_hotfix_count": len(hotfix_logs),
            "unresolved_count": len(unresolved),
            "total_fix_count": len(applied),
        },
        "applied_fixes": [item.as_dict() for item in applied],
        "unresolved": unresolved,
    }

    _write_json(Path(args.report_json), report)
    _write_markdown(Path(args.report_md), report)
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json).resolve()),
                "report_md": str(Path(args.report_md).resolve()),
                "targeted_fix_count": len(targeted_logs),
                "global_e_fix_count": len(global_logs),
                "known_hotfix_count": len(hotfix_logs),
                "unresolved_count": len(unresolved),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
