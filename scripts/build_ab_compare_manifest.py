#!/usr/bin/env python3
"""Build a JSON manifest comparing two extraction outputs (e.g. jat vs wyo worktrees)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.ab_compare import AbCompareSide, ab_compare_paths_for_side, build_ab_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare exam.json + text-review fields from two data_dir/review_dir pairs.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="Repository root (for original_pdf_data and path resolution).",
    )
    parser.add_argument("--label-a", default="jat")
    parser.add_argument("--label-b", default="wyo")
    parser.add_argument(
        "--data-dir-a",
        help="Side A .generated/data path (defaults to .generated/ab-compare/jat/data under repo-root).",
    )
    parser.add_argument(
        "--review-dir-a",
        help="Side A text-verification dir (defaults to ab-compare jat review path).",
    )
    parser.add_argument(
        "--data-dir-b",
        help="Side B data dir (defaults to .generated/ab-compare/wyo/data).",
    )
    parser.add_argument(
        "--review-dir-b",
        help="Side B review dir (defaults to ab-compare wyo review path).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(Path(ROOT) / ".generated" / "ab-compare" / "ab_manifest.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--exam-id",
        dest="exam_ids",
        action="append",
        help="Limit to specific exam_id (repeatable). Default: intersection of both manifests.",
    )
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    da, ra, _, _ = ab_compare_paths_for_side(repo, "jat")
    db, rb, _, _ = ab_compare_paths_for_side(repo, "wyo")
    side_a = AbCompareSide(
        label=args.label_a,
        data_dir=Path(args.data_dir_a or da),
        review_dir=Path(args.review_dir_a or ra),
    )
    side_b = AbCompareSide(
        label=args.label_b,
        data_dir=Path(args.data_dir_b or db),
        review_dir=Path(args.review_dir_b or rb),
    )
    manifest = build_ab_manifest(side_a, side_b, repo_root=repo, exam_ids=args.exam_ids)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": out.as_posix(), "field_count": manifest["field_count"], "diff_count": manifest["diff_count"]}, indent=2))


if __name__ == "__main__":
    main()
