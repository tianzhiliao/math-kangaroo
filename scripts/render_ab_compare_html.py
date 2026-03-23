#!/usr/bin/env python3
"""Render a self-contained HTML viewer for ab_manifest.json (A/B text + PDF link + filters)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AB extraction compare</title>
  <style>
    :root {{
      font-family: system-ui, sans-serif;
      --border: #ccc;
      --bg: #fafafa;
    }}
    body {{ margin: 0; background: var(--bg); }}
    header {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      background: #fff;
      position: sticky; top: 0; z-index: 2;
    }}
    header h1 {{ margin: 0 0 8px 0; font-size: 1.1rem; }}
    .meta {{ font-size: 0.85rem; color: #444; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-top: 8px; }}
    label {{ display: flex; gap: 6px; align-items: center; font-size: 0.9rem; }}
    select, input {{ font: inherit; padding: 4px 8px; }}
    main {{ display: flex; min-height: calc(100vh - 80px); }}
    .main-right {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
    nav {{
      border-right: 1px solid var(--border);
      background: #fff;
      overflow: auto;
      padding: 8px;
    }}
    nav button {{
      display: block; width: 100%; text-align: left;
      padding: 6px 8px; margin-bottom: 4px;
      border: 1px solid transparent; border-radius: 4px;
      background: #f4f4f4; cursor: pointer; font-size: 0.85rem;
    }}
    nav button:hover {{ background: #eaeaea; }}
    nav button.active {{ border-color: #888; background: #e0e8ff; }}
    .exam-head {{ font-weight: 600; font-size: 0.75rem; color: #666; margin: 12px 0 4px; text-transform: uppercase; }}
    .table-wrap {{ flex: 1; overflow: auto; padding: 0 0 48px 0; }}
    .row {{
      display: grid;
      grid-template-columns: 1fr 1fr minmax(200px, 0.85fr);
      gap: 0;
      border-bottom: 1px solid #e8e8e8;
    }}
    .row.head {{
      position: sticky; top: 0; z-index: 1;
      background: #eee;
      font-weight: 600; font-size: 0.85rem;
      border-bottom: 2px solid var(--border);
    }}
    .cell {{
      padding: 10px 12px;
      font-size: 0.88rem;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .cell.meta-small {{ font-size: 0.75rem; color: #555; }}
    .tag {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem; margin-right: 4px; }}
    .tag.diff {{ background: #ffe4e4; }}
    .tag.susp {{ background: #fff3cd; }}
    .pdf-box {{ padding: 10px 12px; border-bottom: 1px solid #e8e8e8; }}
    .pdf-box a {{ word-break: break-all; color: #06c; }}
    .empty {{ padding: 24px; color: #666; }}
  </style>
</head>
<body>
  <header>
    <h1>A/B text extraction compare</h1>
    <div class="meta" id="summary"></div>
    <div class="controls">
      <label>Exam <select id="examFilter"></select></label>
      <label><input type="checkbox" id="onlyDiff" /> Only differences</label>
      <label><input type="checkbox" id="onlySuspicious" /> Any suspicious (A or B)</label>
      <label>Jump <input type="text" id="jumpField" placeholder="q01.stem" style="width:140px" /></label>
    </div>
  </header>
  <main>
    <nav id="nav"></nav>
    <div class="main-right">
    <section class="table-wrap">
      <div class="row head">
        <div class="cell" id="hA"></div>
        <div class="cell" id="hB"></div>
        <div class="cell">PDF / page</div>
      </div>
      <div id="rows"></div>
    </section>
    </div>
  </main>
  <script type="application/json" id="manifest-data">__MANIFEST_JSON__</script>
  <script>
  (function() {{
    const raw = document.getElementById('manifest-data').textContent;
    const MANIFEST = JSON.parse(raw);
    const labelA = MANIFEST.side_a.label;
    const labelB = MANIFEST.side_b.label;
    document.getElementById('hA').textContent = labelA + ' (exam.json text)';
    document.getElementById('hB').textContent = labelB + ' (exam.json text)';
    const summary = MANIFEST;
    document.getElementById('summary').textContent =
      'Exams: ' + summary.exam_count + ', fields: ' + summary.field_count +
      ', raw diffs: ' + summary.diff_count +
      ' | A: ' + summary.side_a.data_dir + ' | B: ' + summary.side_b.data_dir;

    const rowsByExam = {{}};
    for (const r of MANIFEST.rows) {{
      if (!rowsByExam[r.exam_id]) rowsByExam[r.exam_id] = [];
      rowsByExam[r.exam_id].push(r);
    }}
    const examSummaries = {{}};
    for (const s of MANIFEST.exam_summaries || []) {{
      examSummaries[s.exam_id] = s;
    }}

    const examFilter = document.getElementById('examFilter');
    const onlyDiff = document.getElementById('onlyDiff');
    const onlySusp = document.getElementById('onlySuspicious');
    const jumpField = document.getElementById('jumpField');
    MANIFEST.exam_ids.forEach((id) => {{
      const opt = document.createElement('option');
      opt.value = id; opt.textContent = id;
      examFilter.appendChild(opt);
    }});

    function fileUrl(path) {{
      if (!path) return '';
      const p = String(path).replace(/\\\\/g, '/');
      if (p.startsWith('file:')) return p;
      const enc = encodeURI(p).replace(/#/g, '%23');
      return 'file://' + (p.startsWith('/') ? '' : '/') + enc;
    }}

    function renderNav() {{
      const nav = document.getElementById('nav');
      nav.innerHTML = '';
      const examId = examFilter.value;
      const h = document.createElement('div');
      h.className = 'exam-head';
      h.textContent = examId;
      nav.appendChild(h);
      const list = rowsByExam[examId] || [];
      for (const r of list) {{
        const od = onlyDiff.checked && r.same_raw;
        const os = onlySusp.checked && !r.any_suspicious;
        if (od || os) continue;
        const btn = document.createElement('button');
        btn.textContent = r.field_id + (r.same_raw ? '' : ' *');
        if (!r.same_raw) btn.style.fontWeight = '600';
        btn.onclick = () => {{ jumpField.value = r.field_id; renderRows(); scrollToField(r.field_id); }};
        nav.appendChild(btn);
      }}
    }}

    function scrollToField(fid) {{
      const el = document.getElementById('field-' + fid.replace(/[^a-zA-Z0-9._-]/g, '_'));
      if (el) el.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
    }}

    function renderRows() {{
      const examId = examFilter.value;
      const list = (rowsByExam[examId] || []).filter((r) => {{
        if (onlyDiff.checked && r.same_raw) return false;
        if (onlySusp.checked && !r.any_suspicious) return false;
        return true;
      }});
      const rowsEl = document.getElementById('rows');
      rowsEl.innerHTML = '';
      const sum = examSummaries[examId];
      const pdfPath = sum && sum.source_pdf_resolved;
      const mm = sum && sum.side_a && sum.side_a.mismatch_count;
      const pageHint = mm ? (' (answer mismatches: ' + mm + ')') : '';

      if (list.length === 0) {{
        const empty = document.createElement('div');
        empty.className = 'empty';
        empty.textContent = 'No rows match filters.';
        rowsEl.appendChild(empty);
        return;
      }}

      for (const r of list) {{
        const idSafe = 'field-' + r.field_id.replace(/[^a-zA-Z0-9._-]/g, '_');
        const row = document.createElement('div');
        row.className = 'row';
        const c1 = document.createElement('div');
        c1.className = 'cell';
        c1.id = idSafe;
        let h = '';
        if (!r.same_raw) h += '<span class="tag diff">diff</span>';
        if (r.any_suspicious) h += '<span class="tag susp">suspicious</span>';
        h += escapeHtml(r.text_a);
        c1.innerHTML = h;
        const c2 = document.createElement('div');
        c2.className = 'cell';
        c2.innerHTML = escapeHtml(r.text_b);
        const c3 = document.createElement('div');
        c3.className = 'cell meta-small pdf-box';
        if (pdfPath && r.page) {{
          const u = fileUrl(pdfPath) + '#page=' + encodeURIComponent(String(r.page));
          c3.innerHTML = 'Page ' + r.page + '<br/><a href="' + u + '" target="_blank" rel="noopener">Open PDF</a>';
        }} else if (pdfPath) {{
          c3.innerHTML = '<a href="' + fileUrl(pdfPath) + '" target="_blank" rel="noopener">Open PDF</a>';
        }} else {{
          c3.textContent = 'PDF path unavailable' + pageHint;
        }}
        row.appendChild(c1);
        row.appendChild(c2);
        row.appendChild(c3);
        rowsEl.appendChild(row);
      }}
    }}

    function escapeHtml(s) {{
      const d = document.createElement('div');
      d.textContent = s;
      return d.innerHTML;
    }}

    examFilter.onchange = () => {{ renderNav(); renderRows(); }};
    onlyDiff.onchange = () => {{ renderNav(); renderRows(); }};
    onlySusp.onchange = () => {{ renderNav(); renderRows(); }};
    jumpField.onchange = () => {{
      const fid = jumpField.value.trim();
      for (const r of MANIFEST.rows) {{
        if (r.field_id === fid) {{ examFilter.value = r.exam_id; renderNav(); renderRows(); scrollToField(fid); return; }}
      }}
    }};

    renderNav();
    renderRows();
  }})();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render ab_compare HTML from manifest JSON.")
    parser.add_argument(
        "--manifest",
        default=str(ROOT / ".generated" / "ab-compare" / "ab_manifest.json"),
        help="Path to ab_manifest.json from build_ab_compare_manifest.py",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(ROOT / ".generated" / "ab-compare" / "ab_compare.html"),
    )
    args = parser.parse_args()
    mpath = Path(args.manifest)
    if not mpath.exists():
        raise SystemExit(f"Missing manifest: {mpath}")
    payload = json.loads(mpath.read_text(encoding="utf-8"))
    embedded = json.dumps(payload, ensure_ascii=False)
    embedded = embedded.replace("</", "<\\/")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(HTML_TEMPLATE.replace("__MANIFEST_JSON__", embedded), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
