#!/usr/bin/env python3
"""
Run both worktree pipelines into isolated dirs under `.generated/ab-compare/`, then build manifest + HTML.

Requires:
  - Main repo PDFs at `<repo>/original_pdf_data`
  - JAT worktree with `scripts/full_text_refresh_pipeline.py`
  - WYO worktree with `scripts/run_zero_error_pilot.py`

Example:
  python scripts/run_ab_compare_orchestrator.py \\
    --jat-root ~/.cursor/worktrees/math_web_app/jat \\
    --wyo-root ~/.cursor/worktrees/math_web_app/wyo

To only rebuild the viewer from existing outputs:
  python scripts/run_ab_compare_orchestrator.py --skip-jat --skip-wyo
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.ab_compare import AbCompareSide, ab_compare_paths_for_side, build_ab_manifest


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, check=check, text=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run jat vs wyo extraction into ab-compare dirs and render HTML.")
    parser.add_argument("--repo-root", default=str(ROOT))
    default_jat = Path.home() / ".cursor/worktrees/math_web_app/jat"
    default_wyo = Path.home() / ".cursor/worktrees/math_web_app/wyo"
    parser.add_argument("--jat-root", default=str(default_jat), help="Path to jat worktree (full_text_refresh_pipeline).")
    parser.add_argument("--wyo-root", default=str(default_wyo), help="Path to wyo worktree (run_zero_error_pilot).")
    parser.add_argument(
        "--source-dir",
        default="",
        help="PDF source dir (default: <repo-root>/original_pdf_data).",
    )
    parser.add_argument("--skip-jat", action="store_true")
    parser.add_argument("--skip-wyo", action="store_true")
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel workers for wyo zero-error pilot (default 1 avoids review manifest races).",
    )
    parser.add_argument(
        "--wyo-continue-on-fail",
        action="store_true",
        help="Do not exit non-zero if wyo readiness gate fails (still useful for A/B).",
    )
    parser.add_argument(
        "--exam-id",
        dest="exam_ids",
        action="append",
        help="Limit pipeline to these exams (default: all in manifest after initial build).",
    )
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    source = Path(args.source_dir or (repo / "original_pdf_data")).resolve()
    jat_root = Path(args.jat_root).resolve()
    wyo_root = Path(args.wyo_root).resolve()

    jat_data, jat_review, jat_report, jat_release = ab_compare_paths_for_side(repo, "jat")
    wyo_data, wyo_review, wyo_report, wyo_release = ab_compare_paths_for_side(repo, "wyo")

    py = sys.executable

    if not args.skip_jat:
        jat_script = jat_root / "scripts" / "full_text_refresh_pipeline.py"
        if not jat_script.exists():
            raise SystemExit(f"Missing jat script: {jat_script}")
        jat_cmd = [
            py,
            str(jat_script),
            "--source-dir",
            str(source),
            "--data-dir",
            str(jat_data),
            "--review-dir",
            str(jat_review),
            "--text-report-dir",
            str(jat_report),
            "--release-dir",
            str(jat_release),
        ]
        if args.exam_ids:
            for eid in args.exam_ids:
                jat_cmd.extend(["--exam-id", eid])
        jat_cmd.append("--skip-release")
        t0 = time.perf_counter()
        _run(jat_cmd)
        print(f"jat pipeline done in {time.perf_counter() - t0:.1f}s", flush=True)

    if not args.skip_wyo:
        wyo_script = wyo_root / "scripts" / "run_zero_error_pilot.py"
        if not wyo_script.exists():
            raise SystemExit(f"Missing wyo script: {wyo_script}")
        manifest_path = wyo_data / "manifest.json"
        if not manifest_path.exists():
            build_exam = repo / "scripts" / "build_exam_data.py"
            print(f"Seeding wyo data dir via {build_exam}", flush=True)
            _run(
                [
                    py,
                    str(build_exam),
                    "--source-dir",
                    str(source),
                    "--output-dir",
                    str(wyo_data),
                ]
            )
        if not manifest_path.exists():
            raise SystemExit(f"Still missing {manifest_path} after build_exam_data.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        all_ids = [e["exam_id"] for e in manifest.get("exams", [])]
        exam_ids = list(args.exam_ids) if args.exam_ids else all_ids
        if not exam_ids:
            raise SystemExit("No exams in manifest.")
        cmd = [
            py,
            str(wyo_script),
            "--source-dir",
            str(source),
            "--data-dir",
            str(wyo_data),
            "--review-dir",
            str(wyo_review),
            "--report-dir",
            str(wyo_report),
            "--max-rounds",
            str(args.max_rounds),
            "--workers",
            str(args.workers),
        ]
        for eid in exam_ids:
            cmd.extend(["--exam-id", eid])
        t0 = time.perf_counter()
        try:
            _run(cmd)
        except subprocess.CalledProcessError:
            if not args.wyo_continue_on_fail:
                raise
            print("warning: wyo pipeline exited with non-zero (continuing for A/B manifest).", flush=True)
        print(f"wyo pipeline done in {time.perf_counter() - t0:.1f}s", flush=True)

    out_dir = repo / ".generated" / "ab-compare"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_json = out_dir / "ab_manifest.json"
    html_out = out_dir / "ab_compare.html"

    side_a = AbCompareSide(label="jat", data_dir=jat_data, review_dir=jat_review)
    side_b = AbCompareSide(label="wyo", data_dir=wyo_data, review_dir=wyo_review)
    payload = build_ab_manifest(side_a, side_b, repo_root=repo, exam_ids=args.exam_ids)
    manifest_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _run([py, str(repo / "scripts" / "render_ab_compare_html.py"), "--manifest", str(manifest_json), "--output", str(html_out)])

    print(json.dumps({"manifest": manifest_json.as_posix(), "html": html_out.as_posix()}, indent=2))


if __name__ == "__main__":
    main()
