"""Quality audit for AI-generated similar questions under ``generated/``.

Each source question in ``release-data`` may have one generated variant at
``generated/<exam_id>/<question_id>/`` holding ``question.json``, its SVG
figures, ``card.png`` (the rendered question) and ``compare.png`` (source vs
variant, for human review). A per-exam ``manifest.json`` records the status of
every source question, including ``skipped-duplicate`` entries that reuse the
variant of an identical question in another exam.

The audit is structural: it checks the data the web app and API rely on and
flags signs of a weak variant. It does not prove the answer key is right; the
optional solver pass in ``scripts/evaluate_generated_questions.py`` covers that.
"""

from __future__ import annotations

import difflib
import json
import re
import struct
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ERROR = "error"
WARNING = "warning"
INFO = "info"

REQUIRED_FILES = ("question.json", "card.png", "compare.png")
QUESTION_ID_PATTERN = re.compile(r"^q\d{2}$")
SVG_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*\.svg$")
NON_LATIN_PATTERN = re.compile(r"[\u0400-\u04ff\u3000-\u9fff\uac00-\ud7af]")
MIN_CARD_WIDTH = 1600
# Stems this close to the source read as a copy, not a new question.
STEM_COPY_RATIO = 0.97


@dataclass
class Finding:
    exam_id: str
    question_id: str
    severity: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "exam_id": self.exam_id,
            "question_id": self.question_id,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }


@dataclass
class AuditReport:
    source_questions: int = 0
    variants: int = 0
    duplicates: int = 0
    missing: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    answer_distribution: Counter[str] = field(default_factory=Counter)
    source_answer_distribution: Counter[str] = field(default_factory=Counter)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == WARNING]

    @property
    def notes(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == INFO]

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_questions": self.source_questions,
            "variants": self.variants,
            "duplicates": self.duplicates,
            "missing": self.missing,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "info_count": len(self.notes),
            "answer_distribution": dict(sorted(self.answer_distribution.items())),
            "source_answer_distribution": dict(sorted(self.source_answer_distribution.items())),
            "findings": [f.as_dict() for f in self.findings],
        }


def load_release_questions(release_root: Path) -> dict[str, dict[str, Any]]:
    """Map exam_id to its exam.json payload, in manifest order."""
    manifest = json.loads((release_root / "manifest.json").read_text(encoding="utf-8"))
    exams: dict[str, dict[str, Any]] = {}
    for entry in manifest["exams"]:
        exams[entry["exam_id"]] = json.loads(
            (release_root / entry["path"]).read_text(encoding="utf-8")
        )
    return exams


def resolve_variant_dir(
    generated_root: Path, exam_id: str, question_id: str
) -> Path | None:
    """Folder holding the variant for a source question, following duplicates."""
    direct = generated_root / exam_id / question_id
    if (direct / "question.json").is_file():
        return direct
    entry = _manifest_entry(generated_root, exam_id, question_id)
    if not entry or entry.get("status") != "skipped-duplicate":
        return None
    dup_exam = entry.get("duplicate_of")
    dup_question = entry.get("duplicate_question")
    if not isinstance(dup_exam, str) or not isinstance(dup_question, str):
        return None
    target = generated_root / dup_exam / dup_question
    return target if (target / "question.json").is_file() else None


def audit_generated_questions(release_root: Path, generated_root: Path) -> AuditReport:
    report = AuditReport()
    exams = load_release_questions(release_root)

    for exam_id, exam in exams.items():
        manifest = _load_manifest(generated_root, exam_id)
        if manifest is None:
            report.findings.append(
                Finding(exam_id, "-", ERROR, "manifest_missing", "generated manifest.json is missing")
            )
        manifest_ids = {q["id"] for q in (manifest or {}).get("questions", [])}
        source_ids = {q["id"] for q in exam["questions"]}
        for extra in sorted(manifest_ids - source_ids):
            report.findings.append(
                Finding(exam_id, extra, ERROR, "manifest_unknown_question", "manifest lists a question the exam does not have")
            )

        for source in exam["questions"]:
            report.source_questions += 1
            qid = source["id"]
            entry = _manifest_entry(generated_root, exam_id, qid)
            if entry and entry.get("status") == "skipped-duplicate":
                report.duplicates += 1
                _audit_duplicate(report, generated_root, exams, exam_id, source, entry)
                continue

            folder = generated_root / exam_id / qid
            if not (folder / "question.json").is_file():
                report.missing.append(f"{exam_id}/{qid}")
                report.findings.append(
                    Finding(exam_id, qid, ERROR, "variant_missing", "no generated question.json")
                )
                continue
            report.variants += 1
            source_answer = str(exam.get("answer_key", {}).get(str(source["number"]), "")).upper()
            if source_answer:
                report.source_answer_distribution[source_answer] += 1
            answer = audit_variant(
                report.findings,
                folder,
                exam_id=exam_id,
                source=source,
                source_answer=source_answer,
                manifest_entry=entry,
            )
            if answer:
                report.answer_distribution[answer] += 1

    return report


def audit_variant(
    findings: list[Finding],
    folder: Path,
    *,
    exam_id: str,
    source: dict[str, Any],
    source_answer: str,
    manifest_entry: dict[str, Any] | None,
) -> str | None:
    """Check one variant folder. Returns the variant's answer when it is valid."""
    qid = source["id"]

    def add(severity: str, code: str, message: str) -> None:
        findings.append(Finding(exam_id, qid, severity, code, message))

    for name in REQUIRED_FILES:
        if not (folder / name).is_file():
            add(ERROR, "file_missing", f"{name} is missing")

    try:
        question = json.loads((folder / "question.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add(ERROR, "json_invalid", f"question.json does not parse: {exc}")
        return None

    for key, kind in (
        ("id", str),
        ("number", int),
        ("stem_text", str),
        ("answer", str),
        ("choices", list),
        ("shared_asset_refs", list),
        ("assets", list),
    ):
        if not isinstance(question.get(key), kind):
            add(ERROR, "field_invalid", f"`{key}` must be a {kind.__name__}")
    if any(f.code == "field_invalid" and f.question_id == qid and f.exam_id == exam_id for f in findings):
        return None

    if question["id"] != qid:
        add(ERROR, "id_mismatch", f"id is {question['id']!r}, folder is {qid!r}")
    if question["number"] != source["number"]:
        add(ERROR, "number_mismatch", f"number {question['number']} differs from source {source['number']}")
    if source.get("points") is not None and question.get("points") != source.get("points"):
        add(WARNING, "points_mismatch", f"points {question.get('points')} differ from source {source.get('points')}")

    # Choices
    labels = [str(c.get("label", "")) for c in question["choices"]]
    source_labels = [str(c["label"]) for c in source["choices"]]
    if len(set(labels)) != len(labels):
        add(ERROR, "choice_labels_duplicate", f"choice labels repeat: {labels}")
    if labels != source_labels:
        add(WARNING, "choice_labels_differ", f"labels {labels} differ from source {source_labels}")
    answer = question["answer"].strip().upper()
    if answer not in labels:
        add(ERROR, "answer_not_a_choice", f"answer {question['answer']!r} is not one of {labels}")
        answer = ""
    if manifest_entry and manifest_entry.get("answer") and manifest_entry["answer"] != question["answer"]:
        add(ERROR, "manifest_answer_mismatch", f"manifest answer {manifest_entry['answer']} != question answer {question['answer']}")

    assets_by_id: dict[str, dict[str, Any]] = {}
    for asset in question["assets"]:
        asset_id = asset.get("id")
        if not isinstance(asset_id, str):
            add(ERROR, "asset_invalid", "asset without an id")
            continue
        if asset_id in assets_by_id:
            add(ERROR, "asset_duplicate", f"asset id {asset_id} repeats")
        assets_by_id[asset_id] = asset

    texts: list[str] = []
    for choice in question["choices"]:
        text = str(choice.get("text", "")).strip()
        refs = choice.get("asset_refs", [])
        if not isinstance(refs, list):
            add(ERROR, "choice_invalid", f"choice {choice.get('label')} asset_refs is not a list")
            refs = []
        if not text and not refs and not question["shared_asset_refs"]:
            # Letter-only choices are fine when the stem figure labels them.
            add(ERROR, "choice_empty", f"choice {choice.get('label')} has no text and no figure to point at")
        for ref in refs:
            if ref not in assets_by_id:
                add(ERROR, "asset_ref_unknown", f"choice {choice.get('label')} refers to unknown asset {ref}")
        if text:
            texts.append(_normalize_text(text))
        if text and NON_LATIN_PATTERN.search(text):
            add(ERROR, "language", f"choice {choice.get('label')} text is not English: {text!r}")
    repeated = [t for t, n in Counter(texts).items() if n > 1]
    if repeated:
        add(ERROR, "choice_texts_duplicate", f"choices share the same text: {repeated}")

    # Stem
    stem = question["stem_text"].strip()
    if not stem:
        add(ERROR, "stem_empty", "stem_text is empty")
    if NON_LATIN_PATTERN.search(stem):
        add(ERROR, "language", "stem_text is not English")
    source_stem = str(source.get("stem_text", "")).strip()
    if stem and source_stem:
        ratio = difflib.SequenceMatcher(None, _normalize_text(stem), _normalize_text(source_stem)).ratio()
        source_texts = [t for t in (_normalize_text(str(c.get("text", ""))) for c in source["choices"]) if t]
        same_answer = answer == source_answer
        if ratio >= STEM_COPY_RATIO and texts and texts == source_texts and same_answer:
            add(WARNING, "copy_of_source", f"stem and choices match the source (similarity {ratio:.2f})")
        elif ratio >= STEM_COPY_RATIO:
            # Common for picture tasks: same wording, new figure or numbers.
            add(INFO, "stem_reused", f"stem wording matches the source (similarity {ratio:.2f})")

    # Figures
    for ref in question["shared_asset_refs"]:
        if ref not in assets_by_id:
            add(ERROR, "asset_ref_unknown", f"stem refers to unknown asset {ref}")
    referenced = set(question["shared_asset_refs"]) | {
        ref for c in question["choices"] for ref in c.get("asset_refs", []) if isinstance(ref, str)
    }
    for asset_id, asset in assets_by_id.items():
        if asset_id not in referenced:
            add(WARNING, "asset_unused", f"asset {asset_id} is not referenced")
        _audit_svg(add, folder, asset)

    no_figure = bool(manifest_entry and manifest_entry.get("no_figure"))
    has_figure = bool(question["shared_asset_refs"]) or any(c.get("asset_refs") for c in question["choices"])
    if no_figure and has_figure:
        add(WARNING, "no_figure_mismatch", "manifest says no_figure but the question has figures")
    source_has_figure = bool(source.get("shared_asset_refs")) or any(c.get("asset_refs") for c in source["choices"])
    if source_has_figure and not has_figure and not no_figure:
        add(WARNING, "figure_dropped", "source has a figure but the variant has none")

    card = folder / "card.png"
    if card.is_file():
        width = _png_width(card)
        if width is None:
            add(ERROR, "card_invalid", "card.png is not a PNG")
        elif width < MIN_CARD_WIDTH:
            add(WARNING, "card_small", f"card.png is {width}px wide (< {MIN_CARD_WIDTH})")

    return answer or None


def _audit_svg(add, folder: Path, asset: dict[str, Any]) -> None:
    asset_id = asset.get("id")
    path = str(asset.get("path", ""))
    if not SVG_NAME_PATTERN.match(path):
        add(ERROR, "asset_path_invalid", f"asset {asset_id} path {path!r} is not a plain .svg name")
        return
    if asset.get("media_type") != "image/svg+xml" or asset.get("format") != "svg":
        add(WARNING, "asset_type", f"asset {asset_id} format/media_type should be svg / image/svg+xml")
    file = folder / path
    if not file.is_file():
        add(ERROR, "asset_file_missing", f"{path} is missing")
        return
    raw = file.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        add(ERROR, "svg_invalid", f"{path} is not well-formed XML: {exc}")
        return
    if not root.tag.endswith("svg"):
        add(ERROR, "svg_invalid", f"{path} root element is {root.tag}")
    if any(el.tag.endswith("image") for el in root.iter()):
        add(ERROR, "svg_embedded_image", f"{path} embeds a raster <image>")
    if "base64" in raw:
        add(ERROR, "svg_embedded_image", f"{path} contains base64 data")
    if any(el.tag.endswith("script") for el in root.iter()) or re.search(r"\bon[a-z]+\s*=", raw):
        add(ERROR, "svg_script", f"{path} contains script or event handlers")
    if not root.get("viewBox"):
        add(WARNING, "svg_no_viewbox", f"{path} has no viewBox")
    else:
        try:
            _, _, vb_w, vb_h = (float(v) for v in root.get("viewBox", "").replace(",", " ").split())
            width, height = float(asset.get("width", 0)), float(asset.get("height", 0))
            if width and height and abs(vb_w / vb_h - width / height) > 0.02 * (width / height):
                add(WARNING, "svg_aspect", f"{path} viewBox aspect differs from asset width/height")
        except (ValueError, ZeroDivisionError):
            add(WARNING, "svg_no_viewbox", f"{path} has an unreadable viewBox")
    if NON_LATIN_PATTERN.search("".join(el.text or "" for el in root.iter())):
        add(ERROR, "language", f"{path} has non-English text")


def _audit_duplicate(
    report: AuditReport,
    generated_root: Path,
    exams: dict[str, dict[str, Any]],
    exam_id: str,
    source: dict[str, Any],
    entry: dict[str, Any],
) -> None:
    qid = source["id"]
    dup_exam = entry.get("duplicate_of")
    dup_question = entry.get("duplicate_question")
    if not isinstance(dup_exam, str) or not isinstance(dup_question, str):
        report.findings.append(
            Finding(exam_id, qid, ERROR, "duplicate_unresolved", "skipped-duplicate needs duplicate_of and duplicate_question")
        )
        return
    target = resolve_variant_dir(generated_root, exam_id, qid)
    if target is None:
        report.findings.append(
            Finding(exam_id, qid, ERROR, "duplicate_unresolved", f"{dup_exam}/{dup_question} has no variant")
        )
        return
    other = next((q for q in exams.get(dup_exam, {}).get("questions", []) if q["id"] == dup_question), None)
    if other is None:
        report.findings.append(
            Finding(exam_id, qid, ERROR, "duplicate_unresolved", f"{dup_exam}/{dup_question} is not a release question")
        )
        return
    if _normalize_text(other["stem_text"]) != _normalize_text(source["stem_text"]):
        report.findings.append(
            Finding(exam_id, qid, ERROR, "duplicate_mismatch", f"stem differs from {dup_exam}/{dup_question}")
        )
    if [c["label"] for c in other["choices"]] != [c["label"] for c in source["choices"]]:
        report.findings.append(
            Finding(exam_id, qid, ERROR, "duplicate_mismatch", f"choice labels differ from {dup_exam}/{dup_question}")
        )


def _load_manifest(generated_root: Path, exam_id: str) -> dict[str, Any] | None:
    path = generated_root / exam_id / "manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_entry(generated_root: Path, exam_id: str, question_id: str) -> dict[str, Any] | None:
    manifest = _load_manifest(generated_root, exam_id)
    if manifest is None:
        return None
    return next((q for q in manifest.get("questions", []) if q.get("id") == question_id), None)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _png_width(path: Path) -> int | None:
    with path.open("rb") as handle:
        head = handle.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">I", head[16:20])[0]


def render_markdown(report: AuditReport, solver: dict[str, Any] | None = None) -> str:
    lines = [
        "# Generated question evaluation",
        "",
        "Produced by `scripts/evaluate_generated_questions.py`.",
        "",
        "## Coverage",
        "",
        f"- Source questions in release-data: {report.source_questions}",
        f"- Generated variants: {report.variants}",
        f"- Reusing the variant of an identical question: {report.duplicates}",
        f"- Missing: {len(report.missing)}",
        "",
        "## Structural audit",
        "",
        f"- Errors: {len(report.errors)}",
        f"- Warnings: {len(report.warnings)}",
        f"- Notes: {len(report.notes)}",
        "",
    ]
    total = sum(report.answer_distribution.values()) or 1
    source_total = sum(report.source_answer_distribution.values()) or 1
    lines += [
        "Correct letters, variants vs. their source questions. A child who always",
        "picks the most common letter scores its share without reading the question.",
        "",
        "| Letter | Variants | Share | Sources | Share |",
        "|---|---|---|---|---|",
    ]
    letters = sorted(set(report.answer_distribution) | set(report.source_answer_distribution))
    for letter in letters:
        count = report.answer_distribution[letter]
        source_count = report.source_answer_distribution[letter]
        lines.append(
            f"| {letter} | {count} | {count / total:.0%} | {source_count} | {source_count / source_total:.0%} |"
        )
    lines.append("")
    if report.findings:
        by_code = Counter((f.severity, f.code) for f in report.findings)
        lines += ["| Severity | Check | Count |", "|---|---|---|"]
        for (severity, code), count in sorted(by_code.items()):
            lines.append(f"| {severity} | `{code}` | {count} |")
        lines += ["", "### Findings", ""]
        for f in report.findings:
            lines.append(f"- **{f.severity}** `{f.exam_id}/{f.question_id}` `{f.code}`: {f.message}")
        lines.append("")
    else:
        lines += ["No findings.", ""]

    if solver:
        lines += render_solver_markdown(solver)
    return "\n".join(lines).rstrip() + "\n"


def render_solver_markdown(solver: dict[str, Any]) -> list[str]:
    results = solver.get("results", [])
    agree = [r for r in results if r.get("status") == "agree"]
    disagree = [r for r in results if r.get("status") == "disagree"]
    failed = [r for r in results if r.get("status") == "error"]
    lines = [
        "## Independent solve",
        "",
        f"Model `{solver.get('model')}` solved each variant from its card image without seeing the key.",
        "",
        f"- Checked: {len(results)}",
        f"- Agrees with the key: {len(agree)}",
        f"- Disagrees with the key: {len(disagree)}",
        f"- Could not be checked: {len(failed)}",
        "",
    ]
    if disagree:
        lines += [
            "Disagreements need a human look: the key, the figure, or the model may be wrong.",
            "",
            "| Question | Key | Model | Model's reasoning |",
            "|---|---|---|---|",
        ]
        for r in disagree:
            reason = str(r.get("reasoning", "")).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| `{r['exam_id']}/{r['question_id']}` | {r['answer']} | {r['model_answer']} | {reason} |")
        lines.append("")
    if failed:
        lines += ["Not checked:", ""]
        for r in failed:
            lines.append(f"- `{r['exam_id']}/{r['question_id']}`: {r.get('error')}")
        lines.append("")
    return lines
