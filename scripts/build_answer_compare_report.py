#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.answer_compare_report import build_answer_compare_report, validate_answer_compare_report
from kangaroo_pdf.workspace_paths import workspace_paths


def main() -> None:
    paths = workspace_paths(ROOT)
    parser = argparse.ArgumentParser(
        description="Build static answer comparison reports with original PDF answer pages and raw machine answers."
    )
    parser.add_argument("--source-dir", default=str(paths.source_dir))
    parser.add_argument("--data-dir", default=str(paths.data_dir))
    parser.add_argument("--report-dir", default=str(paths.answer_compare_dir))
    parser.add_argument(
        "--exam-id",
        dest="exam_ids",
        action="append",
        help="Build only specific exam_id values. Can be repeated.",
    )
    args = parser.parse_args()

    manifest = build_answer_compare_report(
        source_dir=Path(args.source_dir),
        data_dir=Path(args.data_dir),
        report_dir=Path(args.report_dir),
        exam_ids=args.exam_ids,
    )
    validation = validate_answer_compare_report(
        report_dir=Path(args.report_dir),
        exam_ids=args.exam_ids,
    )

    print(
        json.dumps(
            {
                "report_dir": Path(args.report_dir).resolve().as_posix(),
                "exam_count": manifest["exam_count"],
                "validation": validation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
