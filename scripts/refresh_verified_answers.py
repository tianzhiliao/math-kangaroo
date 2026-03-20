#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.answer_sync import rebuild_and_sync_answers
from kangaroo_pdf.workspace_paths import workspace_paths


def main() -> None:
    paths = workspace_paths(ROOT)
    parser = argparse.ArgumentParser(description="Rebuild answer keys from PDFs and sync only answer-related JSON fields.")
    parser.add_argument("--source-dir", default=str(paths.source_dir))
    parser.add_argument("--data-dir", help="Optional working dataset to update, for example .generated/data.")
    parser.add_argument("--release-dir", default=str(paths.release_dir))
    parser.add_argument("--review-dir", help="Optional review sidecar directory to update alongside --data-dir.")
    parser.add_argument("--dry-run", action="store_true", help="Compute the answer sync summary without writing files.")
    parser.add_argument(
        "--exam-id",
        dest="exam_ids",
        action="append",
        help="Sync only specific exam_id values. Can be repeated.",
    )
    args = parser.parse_args()

    summary = rebuild_and_sync_answers(
        source_dir=Path(args.source_dir),
        data_dir=Path(args.data_dir) if args.data_dir else None,
        release_dir=Path(args.release_dir),
        review_dir=Path(args.review_dir) if args.review_dir else None,
        exam_ids=args.exam_ids,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
