# Worktree A/B extraction comparison (jat vs wyo)

## Why an agent said “no PDF”

Cursor worktrees under `~/.cursor/worktrees/...` usually **do not** contain `original_pdf_data/`. Your main clone at `math_web_app` does. Always pass an explicit PDF root:

```bash
--source-dir /path/to/math_web_app/original_pdf_data
```

Isolated outputs for fair comparison live under:

- `.generated/ab-compare/jat/` — data, review, reports, release
- `.generated/ab-compare/wyo/` — same layout

## One-shot: run pipelines + viewer

From the **main repo** (adjust worktree paths if yours differ):

```bash
python scripts/run_ab_compare_orchestrator.py \
  --jat-root ~/.cursor/worktrees/math_web_app/jat \
  --wyo-root ~/.cursor/worktrees/math_web_app/wyo
```

Artifacts:

- `.generated/ab-compare/ab_manifest.json` — field-level diff + review flags
- `.generated/ab-compare/ab_compare.html` — local viewer

Open the HTML in a browser (double-click or `open .generated/ab-compare/ab_compare.html` on macOS).

**Note:** Some browsers restrict `file://` links to PDFs. If “Open PDF” does nothing, copy the path from `ab_manifest.json` (`source_pdf_resolved`) or open the PDF manually.

## Rebuild viewer only (pipelines already ran)

```bash
python scripts/run_ab_compare_orchestrator.py --skip-jat --skip-wyo
```

Or manually:

```bash
python scripts/build_ab_compare_manifest.py -o .generated/ab-compare/ab_manifest.json
python scripts/render_ab_compare_html.py --manifest .generated/ab-compare/ab_manifest.json
```

## Unified review (optional, detailed PDF + text)

Point the tool at one side’s dirs, e.g. jat:

```bash
python scripts/run_unified_review.py \
  --data-dir .generated/ab-compare/jat/data \
  --review-dir .generated/ab-compare/jat/review-data/text-verification \
  --release-dir .generated/ab-compare/jat/release-data
```

Then open `http://127.0.0.1:8012` for that side.

## How to decide which scheme is “better”

1. **Hard gates (automatic):** For each exam, compare `pass_gate` / counts in `ab_manifest.json` under `exam_summaries` (`changed`, `suspicious`, `pending`, `mismatch`). Prefer fewer failures.
2. **Field diffs:** Use the HTML viewer with **Only differences** to see where `exam.json` text disagrees between jat and wyo.
3. **Human check:** For disputed fields, use **Open PDF** (page from text review when present) and pick the string that matches print.

When metrics tie, prefer the pipeline that is simpler to maintain and re-run (fewer moving parts, clearer reports).
