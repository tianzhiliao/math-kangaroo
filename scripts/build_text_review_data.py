#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.text_review_pipeline import (
    build_text_review_dataset,
    validate_text_review_dataset,
)
from kangaroo_pdf.workspace_paths import workspace_paths


def main() -> None:
    paths = workspace_paths(ROOT)
    parser = argparse.ArgumentParser(
        description="Re-extract question text, build diff reports, and create text verification sidecars."
    )
    parser.add_argument("--source-dir", default=str(paths.source_dir))
    parser.add_argument("--data-dir", default=str(paths.data_dir))
    parser.add_argument("--output-dir", default=str(paths.review_dir))
    parser.add_argument("--report-dir", default=str(paths.text_report_dir))
    parser.add_argument(
        "--exam-id",
        dest="exam_ids",
        action="append",
        help="Process only specific exam_id values. Can be repeated.",
    )
    args = parser.parse_args()

    manifest = build_text_review_dataset(
        source_dir=Path(args.source_dir),
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        report_dir=Path(args.report_dir),
        exam_ids=args.exam_ids,
    )
    validation = validate_text_review_dataset(
        output_dir=Path(args.output_dir),
        report_dir=Path(args.report_dir),
        exam_ids=args.exam_ids,
    )

    print(
        json.dumps(
            {
                "output_dir": Path(args.output_dir).resolve().as_posix(),
                "report_dir": Path(args.report_dir).resolve().as_posix(),
                "exam_count": len(manifest["exams"]),
                "field_count": manifest["field_count"],
                "validation": validation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
