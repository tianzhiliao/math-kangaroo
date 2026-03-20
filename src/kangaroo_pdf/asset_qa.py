from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any


def _href_from(base_file: Path, target_path: Path) -> str:
    return Path(os.path.relpath(target_path, base_file.parent)).as_posix()


def build_asset_qa_page(
    exam_dir: Path,
    qa_exam_dir: Path,
    exam_json: dict[str, Any],
    audit_json: dict[str, Any],
) -> Path:
    qa_exam_dir.mkdir(parents=True, exist_ok=True)
    page_path = qa_exam_dir / "index.html"
    asset_lookup = {asset["id"]: asset for asset in exam_json["assets"]}

    sections: list[str] = []
    for question, audit_question in zip(exam_json["questions"], audit_json["questions"]):
        reference_rel = audit_question.get("qa_reference_path")
        reference_html = (
            f'<img src="{html.escape(_href_from(page_path, qa_exam_dir / reference_rel))}" alt="Question {question["number"]} reference" />'
            if reference_rel
            else '<div class="empty">No reference image</div>'
        )

        stem_cards = []
        for asset_id in question["shared_asset_refs"]:
            asset = asset_lookup[asset_id]
            stem_cards.append(
                f"""
                <figure class="asset-card">
                  <img src="{html.escape(_href_from(page_path, exam_dir / asset['path']))}" alt="{html.escape(asset_id)}" />
                  <figcaption>{html.escape(asset_id)}</figcaption>
                </figure>
                """
            )
        if not stem_cards:
            stem_cards.append('<div class="empty">No stem image</div>')

        option_cards = []
        for choice in question["choices"]:
            asset_parts = []
            for asset_id in choice["asset_refs"]:
                asset = asset_lookup[asset_id]
                asset_parts.append(
                    f"""
                    <figure class="asset-card small">
                      <img src="{html.escape(_href_from(page_path, exam_dir / asset['path']))}" alt="{html.escape(asset_id)}" />
                      <figcaption>{html.escape(asset_id)}</figcaption>
                    </figure>
                    """
                )
            option_cards.append(
                f"""
                <div class="option-card">
                  <div class="option-label">{html.escape(choice['label'])}</div>
                  <div class="option-text">{html.escape(choice['text'] or '(image option)')}</div>
                  <div class="option-assets">{''.join(asset_parts) if asset_parts else '<div class="empty">No option image</div>'}</div>
                </div>
                """
            )

        sections.append(
            f"""
            <section class="question-card" id="q{question['number']:02d}">
              <div class="question-head">
                <div>
                  <h2>Question {question['number']}</h2>
                  <p>Page {question['source']['page']} | Answer {html.escape(question.get('answer') or '-')}</p>
                </div>
                <div class="status">{'Review' if question['source']['needs_review'] else 'OK'}</div>
              </div>
              <div class="grid">
                <div class="panel">
                  <h3>Original Question Region</h3>
                  {reference_html}
                </div>
                <div class="panel">
                  <h3>Stem Text</h3>
                  <p class="text-block">{html.escape(question['stem_text'])}</p>
                  <h3>Stem Images</h3>
                  <div class="asset-grid">{''.join(stem_cards)}</div>
                </div>
              </div>
              <div class="panel">
                <h3>Options</h3>
                <div class="options-grid">{''.join(option_cards)}</div>
              </div>
            </section>
            """
        )

    page_path.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(exam_json['exam_id'])} asset QA</title>
  <style>
    :root {{
      --bg: #f6f2ea;
      --ink: #161513;
      --card: rgba(255,255,255,0.88);
      --line: rgba(22,21,19,0.12);
      --accent: #1d5d9b;
      --muted: #5f5a52;
      --shadow: 0 18px 40px rgba(14, 16, 21, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Helvetica Neue", "Arial", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(29,93,155,0.16), transparent 28rem),
        linear-gradient(180deg, #efe7db, var(--bg));
      color: var(--ink);
    }}
    main {{
      width: min(1280px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 56px;
    }}
    header {{
      margin-bottom: 28px;
      padding: 24px 26px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: var(--card);
      box-shadow: var(--shadow);
    }}
    h1, h2, h3 {{ margin: 0; }}
    p {{ margin: 0; }}
    .meta {{ margin-top: 10px; color: var(--muted); }}
    .question-card {{
      margin-top: 20px;
      padding: 20px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--card);
      box-shadow: var(--shadow);
    }}
    .question-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 16px;
    }}
    .status {{
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(29,93,155,0.12);
      color: var(--accent);
      font-weight: 700;
      font-size: 13px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .panel {{
      padding: 16px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.78);
    }}
    .panel h3 {{
      margin-bottom: 10px;
      font-size: 15px;
    }}
    .panel img {{
      display: block;
      max-width: 100%;
      border-radius: 12px;
      background: white;
    }}
    .text-block {{
      white-space: pre-wrap;
      line-height: 1.55;
      margin-bottom: 14px;
    }}
    .asset-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .asset-card {{
      margin: 0;
      padding: 12px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: white;
    }}
    .asset-card.small {{
      min-height: 120px;
    }}
    .asset-card figcaption {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      word-break: break-all;
    }}
    .options-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
    }}
    .option-card {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: white;
    }}
    .option-label {{
      font-weight: 800;
      font-size: 14px;
      color: var(--accent);
      margin-bottom: 6px;
    }}
    .option-text {{
      min-height: 38px;
      color: var(--muted);
      line-height: 1.45;
      margin-bottom: 10px;
      white-space: pre-wrap;
    }}
    .option-assets {{
      display: grid;
      gap: 10px;
    }}
    .empty {{
      padding: 12px;
      border: 1px dashed var(--line);
      border-radius: 12px;
      color: var(--muted);
      background: rgba(29,93,155,0.05);
      font-size: 13px;
    }}
    @media (max-width: 920px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{html.escape(exam_json['exam_id'])} Asset QA</h1>
      <p class="meta">Questions: {len(exam_json['questions'])} | Assets: {len(exam_json['assets'])} | Warnings: {len(exam_json.get('warnings', []))}</p>
    </header>
    {''.join(sections)}
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return page_path


def build_asset_qa_index(qa_root: Path, exams: list[dict[str, Any]]) -> Path:
    qa_root.mkdir(parents=True, exist_ok=True)
    index_path = qa_root / "index.html"
    cards = []
    for exam in sorted(exams, key=lambda item: item["exam_id"]):
        page_path = qa_root / f"{exam['exam_id']}.html"
        cards.append(
            f"""
            <a class="card" href="{html.escape(_href_from(index_path, page_path))}">
              <h2>{html.escape(exam['exam_id'])}</h2>
              <p>{exam['question_count']} questions</p>
            </a>
            """
        )
    index_path.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Asset QA</title>
  <style>
    body {{
      margin: 0;
      font-family: "Avenir Next", "Helvetica Neue", sans-serif;
      background: #f4efe8;
      color: #1c1b18;
    }}
    main {{
      width: min(1080px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }}
    .card {{
      display: block;
      padding: 18px;
      border-radius: 18px;
      border: 1px solid rgba(18,18,18,0.12);
      background: rgba(255,255,255,0.86);
      text-decoration: none;
      color: inherit;
    }}
    .card h2 {{
      margin: 0 0 8px;
      font-size: 18px;
    }}
    .card p {{
      margin: 0;
      color: #5b564e;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Asset QA</h1>
    <div class="grid">{''.join(cards)}</div>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return index_path
