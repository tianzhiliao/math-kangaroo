#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Text-only extraction review</title>
  <style>
    :root {
      --bg: #f7f7f7;
      --line: #ddd;
      --card: #fff;
      --warn: #fff3cd;
      --danger: #ffe4e4;
    }
    body { margin: 0; background: var(--bg); font-family: system-ui, sans-serif; }
    header { padding: 12px 16px; background: #fff; border-bottom: 1px solid var(--line); position: sticky; top: 0; z-index: 3; }
    h1 { margin: 0; font-size: 1.05rem; }
    .meta { margin-top: 6px; color: #555; font-size: 0.85rem; }
    .controls { margin-top: 10px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; font-size: 0.9rem; }
    main { display: grid; grid-template-columns: 260px 1fr; min-height: calc(100vh - 88px); }
    nav { border-right: 1px solid var(--line); background: #fff; overflow: auto; padding: 10px; }
    nav button {
      width: 100%;
      text-align: left;
      border: 1px solid transparent;
      border-radius: 6px;
      background: #f4f4f4;
      margin-bottom: 6px;
      padding: 7px 8px;
      cursor: pointer;
      font-size: 0.85rem;
    }
    nav button:hover { background: #ececec; }
    section { overflow: auto; padding: 12px; }
    article {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 10px;
    }
    article.warn { border-color: #f1c76d; background: var(--warn); }
    article.error { border-color: #d88; background: var(--danger); }
    .qhead { display: flex; gap: 12px; justify-content: space-between; align-items: baseline; }
    .qhead h2 { margin: 0; font-size: 1rem; }
    .qmeta { color: #555; font-size: 0.8rem; }
    .stem { margin-top: 8px; white-space: pre-wrap; line-height: 1.45; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }
    td, th { border: 1px solid var(--line); padding: 7px; text-align: left; vertical-align: top; }
    .empty { color: #a00; font-weight: 600; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <header>
    <h1>Text-only extraction review</h1>
    <div class="meta" id="meta"></div>
    <div class="controls">
      <label><input type="checkbox" id="onlyIssues" /> Only issues (empty stem/choice)</label>
      <label><input type="checkbox" id="onlyRisk" /> Only high-risk (quality flags)</label>
      <label><input type="checkbox" id="onlyCharAnomaly" /> Only char anomalies</label>
      <label>Jump <input type="text" id="jump" placeholder="q01" style="width:100px" /></label>
    </div>
  </header>
  <main>
    <nav id="nav"></nav>
    <section id="content"></section>
  </main>
  <script type="application/json" id="data">__DATA__</script>
  <script>
  (function() {
    const payload = JSON.parse(document.getElementById("data").textContent);
    const nav = document.getElementById("nav");
    const content = document.getElementById("content");
    const onlyIssues = document.getElementById("onlyIssues");
    const onlyRisk = document.getElementById("onlyRisk");
    const onlyCharAnomaly = document.getElementById("onlyCharAnomaly");
    const jump = document.getElementById("jump");
    const sourcePdf = payload.source_pdf || "";

    function fileUrl(path) {
      if (!path) return "";
      const p = String(path).replace(/\\\\/g, "/");
      if (p.startsWith("file:")) return p;
      const enc = encodeURI(p).replace(/#/g, "%23");
      return "file://" + (p.startsWith("/") ? "" : "/") + enc;
    }

    function questionHasIssue(q) {
      if (!String(q.stem_text || "").trim()) return true;
      return (q.choices || []).some((c) => !String(c.text || "").trim());
    }

    function questionHasRisk(q) {
      const flags = (q.quality && q.quality.risk_flags) || [];
      return flags.length > 0;
    }

    function questionHasCharAnomaly(q) {
      const quality = q.quality || {};
      return Number(quality.illegal_char_count || 0) > 0
        || ((quality.suspicious_tokens || []).length > 0)
        || ((quality.normalization_edits || []).length > 0);
    }

    function build() {
      const only = onlyIssues.checked;
      const riskOnly = onlyRisk.checked;
      const charOnly = onlyCharAnomaly.checked;
      nav.innerHTML = "";
      content.innerHTML = "";
      for (const q of payload.questions || []) {
        const hasIssue = questionHasIssue(q);
        const hasRisk = questionHasRisk(q);
        const hasCharAnomaly = questionHasCharAnomaly(q);
        if (only && !hasIssue) continue;
        if (riskOnly && !hasRisk) continue;
        if (charOnly && !hasCharAnomaly) continue;

        const btn = document.createElement("button");
        btn.textContent = q.id + (hasIssue ? " !" : "") + (hasRisk ? " [risk]" : "") + (hasCharAnomaly ? " [char]" : "");
        btn.onclick = () => {
          const el = document.getElementById(q.id);
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        };
        nav.appendChild(btn);

        const article = document.createElement("article");
        article.id = q.id;
        article.className = hasIssue ? (String(q.stem_text || "").trim() ? "warn" : "error") : "";
        const page = q.source && q.source.page ? Number(q.source.page) : null;
        const pdfHref = page ? (fileUrl(sourcePdf) + "#page=" + encodeURIComponent(String(page))) : fileUrl(sourcePdf);
        const stem = String(q.stem_text || "").trim();
        const stemRaw = String(q.stem_text_raw || stem).trim();
        const quality = q.quality || {};
        const flags = quality.risk_flags || [];
        const suspicious = quality.suspicious_tokens || [];
        const edits = quality.normalization_edits || [];
        article.innerHTML = `
          <div class="qhead">
            <h2>${escapeHtml(q.id)} (${q.number})</h2>
            <div class="qmeta">
              ${page ? "Page " + page + " | " : ""}<a href="${pdfHref}" target="_blank" rel="noopener">Open PDF</a>
            </div>
          </div>
          <div class="qmeta">quality_flags=${flags.length ? escapeHtml(flags.join(", ")) : "none"} | semantic_score=${quality.semantic_readability_score ?? "-"} | illegal_char_count=${quality.illegal_char_count ?? 0} | illegal_char_ratio=${quality.illegal_char_ratio ?? 0}</div>
          <div class="qmeta">suspicious_tokens=${suspicious.length ? escapeHtml(suspicious.join(", ")) : "none"} | normalization_edits=${edits.length}</div>
          <div class="stem"><strong>Stem (clean)</strong><br/>${stem ? escapeHtml(stem) : '<span class="empty">(empty stem)</span>'}</div>
          <div class="stem"><strong>Stem (raw)</strong><br/>${stemRaw ? escapeHtml(stemRaw) : '<span class="empty">(empty stem)</span>'}</div>
          <table>
            <thead><tr><th style="width:80px">Choice</th><th>Text (clean)</th><th>Text (raw)</th></tr></thead>
            <tbody>
              ${(q.choices || []).map((c) => {
                const cleanText = String(c.text || "").trim();
                const rawText = String(c.text_raw || c.text || "").trim();
                return `<tr><td>${escapeHtml(c.label || "")}</td><td>${cleanText ? escapeHtml(cleanText) : '<span class="empty">(empty)</span>'}</td><td>${rawText ? escapeHtml(rawText) : '<span class="empty">(empty)</span>'}</td></tr>`;
              }).join("")}
            </tbody>
          </table>
        `;
        content.appendChild(article);
      }
    }

    function escapeHtml(s) {
      const d = document.createElement("div");
      d.textContent = String(s || "");
      return d.innerHTML;
    }

    document.getElementById("meta").textContent =
      `exam_id=${payload.exam_id} | questions=${payload.question_count} | source=${sourcePdf} | high_risk=${(payload.quality_summary && payload.quality_summary.high_risk_question_count) ?? "n/a"}`;
    onlyIssues.onchange = build;
    onlyRisk.onchange = build;
    onlyCharAnomaly.onchange = build;
    jump.onchange = function() {
      const target = (jump.value || "").trim();
      if (!target) return;
      const el = document.getElementById(target);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    };
    build();
  })();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a static HTML page for text-only extraction review.")
    parser.add_argument("--json", required=True, help="Input text-only JSON file.")
    parser.add_argument("--output-html", required=True, help="Output static HTML file path.")
    args = parser.parse_args()

    input_path = Path(args.json)
    output_path = Path(args.output_html)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    embedded = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(HTML_TEMPLATE.replace("__DATA__", embedded), encoding="utf-8")
    print(json.dumps({"wrote": str(output_path.resolve()), "source_json": str(input_path.resolve())}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
