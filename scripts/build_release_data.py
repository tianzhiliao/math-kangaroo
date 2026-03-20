#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.release_pipeline import (
    build_cleanup_allowlist_report,
    build_release_dataset,
    validate_release_dataset,
)
from kangaroo_pdf.workspace_paths import workspace_paths


def main() -> None:
    paths = workspace_paths(ROOT)
    parser = argparse.ArgumentParser(description="Build and validate a PNG-only frontend release dataset.")
    parser.add_argument("--data-dir", default=str(paths.data_dir))
    parser.add_argument("--output-dir", default=str(paths.release_dir))
    parser.add_argument(
        "--allowlist-report",
        default=str(paths.cleanup_report_path),
    )
    parser.add_argument(
        "--exam-id",
        dest="exam_ids",
        action="append",
        help="Build only specific exam_id values. Can be repeated.",
    )
    args = parser.parse_args()

    allowlist = build_cleanup_allowlist_report(
        data_dir=Path(args.data_dir),
        report_path=Path(args.allowlist_report),
        exam_ids=args.exam_ids,
    )
    manifest = build_release_dataset(
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        exam_ids=args.exam_ids,
    )
    validation = validate_release_dataset(
        output_dir=Path(args.output_dir),
        exam_ids=args.exam_ids,
    )

    print(
        json.dumps(
            {
                "allowlist_report": Path(args.allowlist_report).resolve().as_posix(),
                "release_dir": Path(args.output_dir).resolve().as_posix(),
                "exam_count": len(manifest["exams"]),
                "asset_count": validation["asset_count"],
                "allowlist_summary": allowlist["summary"],
                "validation": validation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
