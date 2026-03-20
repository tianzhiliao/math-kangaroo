from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

from .pipeline import build_exam_id, classify_document, classify_documents, extract_answers

SCHEMA_VERSION = 1
MANIFEST_KEYS = {
    "schema_version",
    "generated_at",
    "source_dir",
    "data_dir",
    "report_dir",
    "exam_count",
    "exams",
}
MANIFEST_EXAM_KEYS = {
    "exam_id",
    "question_count",
    "method",
    "source_document",
    "machine_answer_count",
    "mismatch_count",
    "page_number",
    "path",
    "asset_path",
}


class AnswerCompareValidationError(ValueError):
    pass


def build_answer_compare_report(
    source_dir: Path | str,
    data_dir: Path | str,
    report_dir: Path | str,
    *,
    exam_ids: list[str] | None = None,
) -> dict[str, Any]:
    source_path = Path(source_dir).resolve()
    data_path = Path(data_dir).resolve()
    report_path = Path(report_dir).resolve()

    report_path.mkdir(parents=True, exist_ok=True)
    assets_root = report_path / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)

    manifest = _read_json(data_path / "manifest.json")
    selected_exam_ids = _select_exam_ids(manifest, exam_ids)
    documents = classify_documents(source_path)
    exam_documents = {build_exam_id(document): document for document in documents if not document.is_answer_table}
    answer_documents_by_year = {document.year: document for document in documents if document.is_answer_table}

    manifest_exams: list[dict[str, Any]] = []
    index_payloads: list[dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc)

    for exam_id in selected_exam_ids:
        exam_json = _read_json(data_path / "exams" / exam_id / "exam.json")
        audit_json = _read_json(data_path / "exams" / exam_id / "audit.json")
        exam_document = exam_documents.get(exam_id)
        if exam_document is None:
            exam_document = classify_document(_resolve_path(source_path, exam_json["source_pdf"]))

        source_pdf_path = _resolve_path(source_path, exam_document.path)
        answer_document = answer_documents_by_year.get(exam_document.year)
        with fitz.open(source_pdf_path.as_posix()) as exam_pdf:
            raw_answer_payload = extract_answers(exam_document, exam_pdf, answer_document)

        answer_source = dict(audit_json.get("answer_source", {}))
        answer_source_path = _resolve_path(source_path, answer_source.get("document") or exam_document.path)
        method = str(answer_source.get("method") or raw_answer_payload.get("method") or "")
        answer_page_number = _answer_page_number(answer_source_path, method)

        asset_dir = assets_root / exam_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        asset_rel_path = Path("assets") / exam_id / "answer-page.png"
        _render_answer_page(answer_source_path, answer_page_number, report_path / asset_rel_path)

        mismatch_questions = _normalize_question_numbers(answer_source.get("mismatch_questions", []))
        detail_payload = _build_exam_payload(
            exam_id=exam_id,
            exam_json=exam_json,
            raw_answer_payload=raw_answer_payload,
            answer_source_path=answer_source_path,
            answer_page_number=answer_page_number,
            method=method,
            mismatch_questions=mismatch_questions,
            asset_path=asset_rel_path.as_posix(),
        )
        detail_path = report_path / f"{exam_id}.html"
        detail_path.write_text(_exam_report_html(detail_payload), encoding="utf-8")

        machine_answer_count = sum(1 for answer in raw_answer_payload.get("answers", {}).values() if answer)
        manifest_entry = {
            "exam_id": exam_id,
            "question_count": int(exam_json.get("question_count", 0)),
            "method": method,
            "source_document": answer_source_path.name,
            "machine_answer_count": machine_answer_count,
            "mismatch_count": len(mismatch_questions),
            "page_number": answer_page_number,
            "path": detail_path.name,
            "asset_path": asset_rel_path.as_posix(),
        }
        manifest_exams.append(manifest_entry)
        index_payloads.append(dict(manifest_entry))

    (report_path / "index.html").write_text(
        _index_report_html(index_payloads=index_payloads, generated_at=generated_at),
        encoding="utf-8",
    )

    output_manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "source_dir": source_path.as_posix(),
        "data_dir": data_path.as_posix(),
        "report_dir": report_path.as_posix(),
        "exam_count": len(manifest_exams),
        "exams": manifest_exams,
    }
    _write_json(report_path / "manifest.json", output_manifest)
    return output_manifest


def validate_answer_compare_report(
    report_dir: Path | str,
    *,
    exam_ids: list[str] | None = None,
) -> dict[str, Any]:
    report_path = Path(report_dir).resolve()
    manifest_path = report_path / "manifest.json"
    if not manifest_path.exists():
        raise AnswerCompareValidationError(f"Missing answer compare manifest: {manifest_path}")

    manifest = _read_json(manifest_path)
    _validate_exact_keys(manifest, MANIFEST_KEYS, "answer compare manifest")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise AnswerCompareValidationError(
            f"answer compare manifest schema_version must be {SCHEMA_VERSION}, got {manifest.get('schema_version')!r}"
        )

    selected_exam_ids = set(exam_ids or [])
    entries = [
        entry for entry in manifest.get("exams", []) if not selected_exam_ids or entry.get("exam_id") in selected_exam_ids
    ]
    if selected_exam_ids:
        known_exam_ids = {entry.get("exam_id") for entry in manifest.get("exams", [])}
        missing_exam_ids = sorted(selected_exam_ids - known_exam_ids)
        if missing_exam_ids:
            raise AnswerCompareValidationError(f"Unknown exam_id values: {', '.join(missing_exam_ids)}")
    if not entries:
        raise AnswerCompareValidationError("No exams matched the requested answer compare scope.")

    index_path = report_path / "index.html"
    if not index_path.exists():
        raise AnswerCompareValidationError(f"Missing answer compare index: {index_path}")

    for entry in entries:
        _validate_exact_keys(entry, MANIFEST_EXAM_KEYS, f"manifest entry {entry.get('exam_id')}")
        detail_path = report_path / entry["path"]
        asset_path = report_path / entry["asset_path"]
        if not detail_path.exists():
            raise AnswerCompareValidationError(f"Missing detail report for {entry['exam_id']}: {detail_path}")
        if not asset_path.exists():
            raise AnswerCompareValidationError(f"Missing answer image for {entry['exam_id']}: {asset_path}")

        detail_html = detail_path.read_text(encoding="utf-8")
        expected_src = f'src="{html.escape(entry["asset_path"])}"'
        if expected_src not in detail_html:
            raise AnswerCompareValidationError(
                f"Detail report for {entry['exam_id']} does not reference the expected relative answer image path."
            )
        if 'src="/' in detail_html or "file://" in detail_html:
            raise AnswerCompareValidationError(
                f"Detail report for {entry['exam_id']} contains a non-portable image reference."
            )

    return {
        "report_dir": report_path.as_posix(),
        "exam_count": len(entries),
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_exam_payload(
    *,
    exam_id: str,
    exam_json: dict[str, Any],
    raw_answer_payload: dict[str, Any],
    answer_source_path: Path,
    answer_page_number: int,
    method: str,
    mismatch_questions: list[int],
    asset_path: str,
) -> dict[str, Any]:
    final_answer_key = {str(key): str(value) for key, value in dict(exam_json.get("answer_key", {})).items()}
    mismatch_set = set(mismatch_questions)
    answer_cards: list[dict[str, Any]] = []
    question_count = int(exam_json.get("question_count", 0))
    for number in range(1, question_count + 1):
        key = str(number)
        raw_answer = str(raw_answer_payload.get("answers", {}).get(key, "") or "")
        final_answer = str(final_answer_key.get(key, "") or "")
        confidence = float(raw_answer_payload.get("confidence_by_question", {}).get(key, 0.0) or 0.0)
        answer_cards.append(
            {
                "number": number,
                "raw_answer": raw_answer,
                "final_answer": final_answer,
                "confidence": confidence,
                "is_mismatch": number in mismatch_set,
            }
        )

    return {
        "exam_id": exam_id,
        "question_count": question_count,
        "source_document": answer_source_path.name,
        "page_number": answer_page_number,
        "method": method,
        "asset_path": asset_path,
        "mismatch_count": len(mismatch_questions),
        "machine_answer_count": sum(1 for card in answer_cards if card["raw_answer"]),
        "warnings": [str(item) for item in raw_answer_payload.get("warnings", []) if str(item)],
        "answer_cards": answer_cards,
    }


def _answer_page_number(source_document_path: Path, method: str) -> int:
    with fitz.open(source_document_path.as_posix()) as document:
        if method == "embedded_answer_page_underline":
            return len(document)
        if method in {"answer_table_text", "answer_table_ocr"}:
            return 1
        return 1


def _render_answer_page(source_document_path: Path, page_number: int, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source_document_path.as_posix()) as document:
        if page_number < 1 or page_number > len(document):
            raise AnswerCompareValidationError(
                f"Requested page {page_number} is out of range for {source_document_path.name}."
            )
        page = document[page_number - 1]
        page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False).save(output_path.as_posix())


def _normalize_question_numbers(values: Any) -> list[int]:
    numbers: list[int] = []
    for value in values or []:
        try:
            numbers.append(int(value))
        except (TypeError, ValueError):
            continue
    return sorted(set(numbers))


def _select_exam_ids(manifest: dict[str, Any], exam_ids: list[str] | None) -> list[str]:
    selected = set(exam_ids or [])
    exam_entries = manifest.get("exams", [])
    ids = [entry["exam_id"] for entry in exam_entries if not selected or entry["exam_id"] in selected]
    if selected:
        known = {entry["exam_id"] for entry in exam_entries}
        missing = sorted(selected - known)
        if missing:
            raise AnswerCompareValidationError(f"Unknown exam_id values: {', '.join(missing)}")
    if not ids:
        raise AnswerCompareValidationError("No exams matched the requested answer compare scope.")
    return ids


def _resolve_path(source_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (source_dir / path).resolve()


def _validate_exact_keys(payload: dict[str, Any], expected_keys: set[str], label: str) -> None:
    actual_keys = set(payload.keys())
    if actual_keys != expected_keys:
        raise AnswerCompareValidationError(
            f"{label} has unexpected keys: expected {sorted(expected_keys)}, got {sorted(actual_keys)}"
        )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _index_report_html(*, index_payloads: list[dict[str, Any]], generated_at: datetime) -> str:
    cards = []
    for entry in index_payloads:
        cards.append(
            f"""
            <article class="card">
              <p class="eyebrow">{html.escape(entry["method"])}</p>
              <h2><a href="{html.escape(entry["path"])}">{html.escape(entry["exam_id"])}</a></h2>
              <p class="meta">{html.escape(entry["source_document"])}</p>
              <dl>
                <div><dt>Questions</dt><dd>{entry["question_count"]}</dd></div>
                <div><dt>Machine answers</dt><dd>{entry["machine_answer_count"]}</dd></div>
                <div><dt>Mismatches</dt><dd>{entry["mismatch_count"]}</dd></div>
                <div><dt>Answer page</dt><dd>{entry["page_number"]}</dd></div>
              </dl>
            </article>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Answer Compare Index</title>
  <style>
    :root {{
      --paper: #f4efe2;
      --panel: rgba(255, 251, 244, 0.94);
      --ink: #1b1a17;
      --muted: #625b4d;
      --line: rgba(72, 59, 38, 0.18);
      --accent: #184c74;
      --accent-soft: rgba(24, 76, 116, 0.12);
      --warning: #9a3f2f;
      --shadow: 0 18px 48px rgba(62, 46, 22, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.8), transparent 35%),
        linear-gradient(180deg, #efe7d5 0%, var(--paper) 45%, #f6f2eb 100%);
      color: var(--ink);
    }}
    main {{ width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 48px; }}
    header {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 28px;
      box-shadow: var(--shadow);
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(32px, 5vw, 54px);
      line-height: 0.95;
      letter-spacing: -0.03em;
    }}
    .lede {{
      margin: 0;
      max-width: 720px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.6;
    }}
    .stamp {{
      display: inline-flex;
      margin-top: 16px;
      padding: 7px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 18px;
      margin-top: 22px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 20px;
      box-shadow: var(--shadow);
    }}
    .eyebrow {{
      margin: 0 0 10px;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .card h2 {{
      margin: 0 0 8px;
      font-size: 24px;
      line-height: 1.05;
    }}
    .card a {{ color: inherit; text-decoration: none; }}
    .meta {{
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 13px;
      word-break: break-word;
    }}
    dl {{
      margin: 0;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    dt {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    dd {{
      margin: 4px 0 0;
      font-size: 20px;
      font-weight: 700;
    }}
    @media (max-width: 640px) {{
      main {{ width: min(100vw - 20px, 1180px); }}
      header, .card {{ border-radius: 18px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Answer Compare</h1>
      <p class="lede">Each report lets you compare the original PDF answer page against the latest machine-extracted raw answers. Mismatch cards call out where the verified final answer differs from the raw extraction.</p>
      <p class="stamp">Generated {html.escape(generated_at.isoformat())}</p>
    </header>
    <section class="grid">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""


def _exam_report_html(payload: dict[str, Any]) -> str:
    warning_html = ""
    if payload["warnings"]:
        warning_items = "".join(f"<li>{html.escape(warning)}</li>" for warning in payload["warnings"])
        warning_html = f"""
        <section class="warnings">
          <h2>Extraction warnings</h2>
          <ul>{warning_items}</ul>
        </section>
        """

    cards = []
    for card in payload["answer_cards"]:
        state_class = "answer-card mismatch" if card["is_mismatch"] else "answer-card"
        badge = '<span class="badge">Mismatch</span>' if card["is_mismatch"] else ""
        confidence = f"{card['confidence']:.3f}".rstrip("0").rstrip(".") if card["confidence"] else "0"
        answer_markup = f"""
          <div class="answer-value">
            <span class="label">Machine</span>
            <strong>{html.escape(card["raw_answer"] or "?")}</strong>
          </div>
        """
        if card["is_mismatch"]:
            answer_markup += f"""
          <div class="answer-arrow">-></div>
          <div class="answer-value final">
            <span class="label">Final</span>
            <strong>{html.escape(card["final_answer"] or "?")}</strong>
          </div>
        """
        cards.append(
            f"""
            <article class="{state_class}">
              <div class="answer-head">
                <h3>Q{card["number"]:02d}</h3>
                {badge}
              </div>
              <div class="answer-values">{answer_markup}</div>
              <p class="confidence">Confidence {html.escape(confidence)}</p>
            </article>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(payload["exam_id"])} Answer Compare</title>
  <style>
    :root {{
      --paper: #f3ecdf;
      --panel: rgba(255, 251, 245, 0.95);
      --ink: #181613;
      --muted: #625c53;
      --line: rgba(69, 58, 34, 0.18);
      --accent: #1a4d76;
      --accent-soft: rgba(26, 77, 118, 0.12);
      --mismatch: #8c3527;
      --mismatch-soft: rgba(140, 53, 39, 0.12);
      --shadow: 0 20px 54px rgba(59, 42, 20, 0.14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(255,255,255,0.7), transparent 28%),
        linear-gradient(180deg, #efe5d2 0%, var(--paper) 42%, #f7f4ee 100%);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    main {{ width: min(1380px, calc(100vw - 28px)); margin: 0 auto; padding: 24px 0 48px; }}
    header {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 26px;
      padding: 22px 24px 26px;
      box-shadow: var(--shadow);
    }}
    .back {{
      display: inline-flex;
      margin-bottom: 14px;
      padding: 6px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .title-row {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-end;
      gap: 18px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(34px, 6vw, 64px);
      line-height: 0.92;
      letter-spacing: -0.04em;
    }}
    .subtitle {{
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.6;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat {{
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid var(--line);
    }}
    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .stat strong {{
      display: block;
      margin-top: 6px;
      font-size: clamp(16px, 2vw, 22px);
      line-height: 1.08;
      overflow-wrap: anywhere;
    }}
    .split {{
      display: grid;
      grid-template-columns: minmax(0, 1.08fr) minmax(340px, 0.92fr);
      gap: 18px;
      margin-top: 20px;
      align-items: start;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 20px;
      box-shadow: var(--shadow);
    }}
    .panel h2 {{
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1;
    }}
    .panel .meta {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }}
    .page-shell {{
      margin-top: 16px;
      border-radius: 18px;
      overflow: hidden;
      border: 1px solid var(--line);
      background: #fffdfa;
    }}
    .page-shell img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .answers-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .answer-card {{
      padding: 14px;
      border-radius: 18px;
      background: rgba(255,255,255,0.78);
      border: 1px solid var(--line);
    }}
    .answer-card.mismatch {{
      border-color: rgba(140, 53, 39, 0.26);
      background: linear-gradient(180deg, rgba(255,255,255,0.96), var(--mismatch-soft));
    }}
    .answer-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    }}
    .answer-head h3 {{
      margin: 0;
      font-size: 19px;
    }}
    .badge {{
      display: inline-flex;
      padding: 5px 9px;
      border-radius: 999px;
      background: rgba(140, 53, 39, 0.14);
      color: var(--mismatch);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .answer-values {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 12px;
      min-height: 66px;
    }}
    .answer-value {{
      min-width: 0;
    }}
    .answer-value .label {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .answer-value strong {{
      display: block;
      margin-top: 5px;
      font-family: "Courier New", Courier, monospace;
      font-size: 34px;
      line-height: 1;
    }}
    .answer-arrow {{
      color: var(--mismatch);
      font-size: 18px;
      font-weight: 700;
    }}
    .confidence {{
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .warnings {{
      margin-top: 18px;
      background: var(--panel);
      border: 1px solid rgba(140, 53, 39, 0.18);
      border-radius: 22px;
      padding: 18px 20px;
      box-shadow: var(--shadow);
    }}
    .warnings h2 {{
      margin: 0 0 10px;
      font-size: 22px;
    }}
    .warnings ul {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
    }}
    @media (max-width: 980px) {{
      .split {{ grid-template-columns: 1fr; }}
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 640px) {{
      main {{ width: min(100vw - 18px, 1380px); }}
      header, .panel, .warnings {{ border-radius: 18px; }}
      .stats {{ grid-template-columns: 1fr; }}
      .answers-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <a class="back" href="index.html">Back to index</a>
      <div class="title-row">
        <div>
          <h1>{html.escape(payload["exam_id"])}</h1>
          <p class="subtitle">Left: original PDF answer page. Right: latest machine-extracted raw answers. Only mismatch cards show the final verified answer for quick comparison.</p>
        </div>
      </div>
      <section class="stats">
        <article class="stat"><span>Method</span><strong>{html.escape(payload["method"])}</strong></article>
        <article class="stat"><span>Source document</span><strong>{html.escape(payload["source_document"])}</strong></article>
        <article class="stat"><span>Questions</span><strong>{payload["question_count"]}</strong></article>
        <article class="stat"><span>Mismatches</span><strong>{payload["mismatch_count"]}</strong></article>
      </section>
    </header>

    <section class="split">
      <article class="panel">
        <h2>Original PDF answer page</h2>
        <p class="meta">{html.escape(payload["source_document"])} - page {payload["page_number"]}</p>
        <div class="page-shell">
          <img src="{html.escape(payload["asset_path"])}" alt="Rendered answer page from {html.escape(payload["source_document"])}" />
        </div>
      </article>

      <article class="panel">
        <h2>Machine extracted raw answers</h2>
        <p class="meta">{payload["machine_answer_count"]} answers detected. Mismatch cards expose the final verified answer beside the raw extraction.</p>
        <div class="answers-grid">
          {''.join(cards)}
        </div>
      </article>
    </section>

    {warning_html}
  </main>
</body>
</html>
"""
