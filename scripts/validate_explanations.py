#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.explanations import exams_with_explanations, stamp_content_hashes, validate_exam
from kangaroo_pdf.workspace_paths import workspace_paths


def main() -> None:
    paths = workspace_paths(ROOT)
    parser = argparse.ArgumentParser(
        description=(
            "Validate pre-generated explanations for original questions (release-data/exams/<id>/explanations.json) "
            "and similar questions (generated/<id>/<qid>/explanation.json)."
        )
    )
    parser.add_argument("--release-dir", default=str(paths.release_dir))
    parser.add_argument("--generated-dir", default=str(ROOT / "generated"))
    parser.add_argument(
        "--exam-id",
        dest="exam_ids",
        action="append",
        help="Validate only specific exam_id values. Can be repeated. Defaults to every exam with explanation files.",
    )
    parser.add_argument("--all", action="store_true", help="Validate every exam in the release manifest.")
    parser.add_argument(
        "--stamp-hashes",
        action="store_true",
        help="Before validating, fill in empty content_hash fields from the current questions.",
    )
    args = parser.parse_args()

    release_dir = Path(args.release_dir).resolve()
    generated_dir = Path(args.generated_dir).resolve()
    if args.all:
        manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
        exam_ids = [entry["exam_id"] for entry in manifest["exams"]]
    else:
        exam_ids = args.exam_ids or exams_with_explanations(release_dir, generated_dir)

    stamped: list[str] = []
    if args.stamp_hashes:
        for exam_id in exam_ids:
            stamped.extend(stamp_content_hashes(release_dir, generated_dir, exam_id))

    reports = [validate_exam(release_dir, generated_dir, exam_id) for exam_id in exam_ids]
    summary = {
        "exams": len(reports),
        "checked": sum(report["checked"] for report in reports),
        "stamped": stamped,
        "errors": {key: value for report in reports for key, value in report["errors"].items()},
        "flagged": [item for report in reports for item in report["flagged"]],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.exit(1 if summary["errors"] else 0)


if __name__ == "__main__":
    main()
