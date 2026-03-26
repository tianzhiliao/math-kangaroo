#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "release-data" / "manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / ".generated" / "reports" / "text-anomaly-scan"

# Typical mojibake / broken-decoding artifacts.
MOJIBAKE_RE = re.compile(
    r"(?:Ã.|Â[^\s]|â€|â€œ|â€|â€˜|â€™|ï¿½|�)"
)

# Header/footer/instruction leakage likely contaminating option text.
OPTION_POLLUTION_RE = re.compile(
    r"(?:"
    r"\bPART\s+[A-Z]\b|"
    r"\b\d+\s*Point Questions?\b|"
    r"\bPoints?\s+Problems?\b|"
    r"\bName:\b|\bSchool:\b|\bClass:\b|"
    r"\bAll rights reserved\b|\bCopyright\b|"
    r"\bMath Kangaroo\b|"
    r"\bPage\s+\d+\b"
    r")",
    re.IGNORECASE,
)

# Noisy OCR fragments and symbol bursts often observed in bad extraction.
OCR_GARBLED_RE = re.compile(
    r"(?:"
    r"\b(?:fe\}|fo\}|co\}|om|rh|ia)\b|"
    r"(?:[°{}\\@|~]){2,}|"
    r"(?:\b[A-Za-z]\b\s+){4,}\b[A-Za-z]\b"
    r")"
)

SPLIT_WORD_RE = re.compile(r"\b[A-Za-z]{2,}\s*-\s+[A-Za-z]{2,}\b")


@dataclass
class Finding:
    exam_id: str
    question_number: int
    field: str
    choice_label: str | None
    issue_type: str
    snippet: str
    rule_hit: str
    risk_score: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "exam_id": self.exam_id,
            "question_number": self.question_number,
            "field": self.field,
            "choice_label": self.choice_label,
            "issue_type": self.issue_type,
            "snippet": self.snippet,
            "rule_hit": self.rule_hit,
            "risk_score": self.risk_score,
        }


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _snippet(text: str, max_len: int = 140) -> str:
    compact = _collapse(text)
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + "..."


def _contains_control_chars(text: str) -> bool:
    for ch in text:
        if unicodedata.category(ch).startswith("C") and ch not in ("\n", "\t", "\r"):
            return True
    return False


def _symbol_noise_score(text: str) -> float:
    if not text:
        return 0.0
    symbols = sum(1 for ch in text if ch in "{}\\@|~°^")
    return symbols / max(1, len(text))


def _is_empty_image_option(text: str, choice: dict[str, Any]) -> bool:
    return (not _collapse(text)) and bool(choice.get("asset_refs"))


def _is_legit_points_sentence(text: str) -> bool:
    # Avoid false positives like "Each goal is worth 2 points."
    compact = _collapse(text)
    return bool(re.search(r"\b\d+\s+points?\b.*\b(each|goal|worth|score)\b", compact, re.IGNORECASE))


def _analyze_field(
    *,
    exam_id: str,
    question_number: int,
    field: str,
    choice_label: str | None,
    text: str,
    is_option: bool,
    has_asset_refs: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    raw = text or ""
    compact = _collapse(raw)

    if is_option and has_asset_refs and not compact:
        return findings

    if _contains_control_chars(raw):
        findings.append(
            Finding(
                exam_id,
                question_number,
                field,
                choice_label,
                "garbled_symbols",
                _snippet(raw),
                "control_characters",
                88,
            )
        )

    if MOJIBAKE_RE.search(raw):
        findings.append(
            Finding(
                exam_id,
                question_number,
                field,
                choice_label,
                "garbled_symbols",
                _snippet(raw),
                "mojibake_pattern",
                90,
            )
        )

    symbol_ratio = _symbol_noise_score(raw)
    if symbol_ratio >= 0.08 or OCR_GARBLED_RE.search(raw):
        findings.append(
            Finding(
                exam_id,
                question_number,
                field,
                choice_label,
                "garbled_symbols",
                _snippet(raw),
                "ocr_or_symbol_noise",
                80 if symbol_ratio >= 0.08 else 74,
            )
        )

    if is_option and compact:
        if OPTION_POLLUTION_RE.search(compact):
            if not _is_legit_points_sentence(compact):
                findings.append(
                    Finding(
                        exam_id,
                        question_number,
                        field,
                        choice_label,
                        "option_pollution",
                        _snippet(raw),
                        "header_footer_instruction_leak",
                        95,
                    )
                )

        # Keep this narrow: only obvious line-break hyphen splits (e.g. "me- tres").
        if SPLIT_WORD_RE.search(compact):
            if len(compact) >= 8:
                findings.append(
                    Finding(
                        exam_id,
                        question_number,
                        field,
                        choice_label,
                        "garbled_symbols",
                        _snippet(raw),
                        "hyphen_linebreak_split",
                        52,
                    )
                )

    return findings


def _dedupe_findings(items: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, int, str, str | None, str, str]] = set()
    deduped: list[Finding] = []
    for item in items:
        key = (
            item.exam_id,
            item.question_number,
            item.field,
            item.choice_label,
            item.issue_type,
            item.rule_hit,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _scan_exam(exam_id: str, exam_payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for q in exam_payload.get("questions", []):
        qn = int(q.get("number", 0))
        stem_text = q.get("stem_text", "")
        findings.extend(
            _analyze_field(
                exam_id=exam_id,
                question_number=qn,
                field="stem_text",
                choice_label=None,
                text=stem_text,
                is_option=False,
                has_asset_refs=False,
            )
        )
        for choice in q.get("choices", []):
            label = str(choice.get("label", ""))
            ctext = choice.get("text", "")
            findings.extend(
                _analyze_field(
                    exam_id=exam_id,
                    question_number=qn,
                    field="choice_text",
                    choice_label=label,
                    text=ctext,
                    is_option=True,
                    has_asset_refs=bool(choice.get("asset_refs")),
                )
            )
    return _dedupe_findings(findings)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _markdown_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Text Anomaly Scan Report")
    lines.append("")
    lines.append(f"- generated_at: `{payload['generated_at']}`")
    lines.append(f"- exam_count: `{payload['summary']['exam_count']}`")
    lines.append(f"- finding_count: `{payload['summary']['finding_count']}`")
    lines.append(
        f"- issue_breakdown: `garbled_symbols={payload['summary']['issue_breakdown']['garbled_symbols']}`, "
        f"`option_pollution={payload['summary']['issue_breakdown']['option_pollution']}`"
    )
    lines.append("")

    by_exam: dict[str, list[dict[str, Any]]] = payload["findings_by_exam"]
    for exam_id in sorted(by_exam.keys()):
        lines.append(f"## {exam_id}")
        lines.append("")
        lines.append("| q | field | issue_type | risk | snippet | rule_hit |")
        lines.append("|---|---|---|---:|---|---|")
        for item in by_exam[exam_id]:
            field_name = item["field"]
            if item.get("choice_label"):
                field_name = f"{field_name}[{item['choice_label']}]"
            snippet = item["snippet"].replace("|", "\\|")
            rule = item["rule_hit"].replace("|", "\\|")
            lines.append(
                f"| {item['question_number']} | {field_name} | {item['issue_type']} | "
                f"{item['risk_score']} | {snippet} | {rule} |"
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan release exam text for likely extraction anomalies (garbled symbols and option pollution)."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to release manifest.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for output reports")
    parser.add_argument("--min-risk", type=int, default=50, help="Drop findings below this risk score")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    output_dir = Path(args.output_dir).resolve()
    release_root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    all_findings: list[Finding] = []
    for exam_entry in manifest.get("exams", []):
        exam_id = exam_entry["exam_id"]
        exam_path = release_root / exam_entry["path"]
        exam_payload = json.loads(exam_path.read_text(encoding="utf-8"))
        all_findings.extend(_scan_exam(exam_id, exam_payload))

    filtered = [f for f in all_findings if f.risk_score >= args.min_risk]
    filtered.sort(key=lambda x: (-x.risk_score, x.exam_id, x.question_number, x.field, x.choice_label or ""))

    findings_by_exam: dict[str, list[dict[str, Any]]] = {}
    for f in filtered:
        findings_by_exam.setdefault(f.exam_id, []).append(f.to_dict())

    issue_breakdown = {"garbled_symbols": 0, "option_pollution": 0}
    for f in filtered:
        if f.issue_type in issue_breakdown:
            issue_breakdown[f.issue_type] += 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_path": manifest_path.as_posix(),
        "summary": {
            "exam_count": len(manifest.get("exams", [])),
            "finding_count": len(filtered),
            "issue_breakdown": issue_breakdown,
            "min_risk": args.min_risk,
        },
        "findings": [f.to_dict() for f in filtered],
        "findings_by_exam": findings_by_exam,
    }

    json_path = output_dir / "findings.json"
    md_path = output_dir / "findings.md"
    _write_json(json_path, payload)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_markdown_report(payload), encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote_json": json_path.as_posix(),
                "wrote_markdown": md_path.as_posix(),
                "finding_count": len(filtered),
                "issue_breakdown": issue_breakdown,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
