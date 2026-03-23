#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.text_only import (
    evaluate_text_only_blocking_errors,
    extract_text_only_exam,
    write_text_only_exam_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract question stem/choices text from one PDF.")
    parser.add_argument("--pdf", required=True, help="Input exam PDF path.")
    parser.add_argument(
        "--output-json",
        required=True,
        help="Output JSON path.",
    )
    parser.add_argument(
        "--qa-gate",
        action="store_true",
        help="Fail command if extraction quality exceeds thresholds.",
    )
    parser.add_argument(
        "--max-high-risk",
        type=int,
        default=0,
        help="Allowed high-risk question count when --qa-gate is enabled.",
    )
    parser.add_argument(
        "--max-option-alignment-conflict",
        type=int,
        default=0,
        help="Allowed option alignment conflict count when --qa-gate is enabled.",
    )
    parser.add_argument(
        "--max-illegal-char-ratio",
        type=float,
        default=0.0,
        help="Allowed max illegal char ratio when --qa-gate is enabled.",
    )
    args = parser.parse_args()

    payload = extract_text_only_exam(Path(args.pdf))
    blocking_errors = evaluate_text_only_blocking_errors(
        payload,
        max_high_risk=args.max_high_risk,
        max_option_alignment_conflict=args.max_option_alignment_conflict,
        max_illegal_char_ratio=args.max_illegal_char_ratio,
    )
    payload["blocking_errors"] = blocking_errors
    write_text_only_exam_json(Path(args.output_json), payload)
    print(
        json.dumps(
            {
                "wrote": str(Path(args.output_json).resolve()),
                "exam_id": payload["exam_id"],
                "question_count": payload["question_count"],
                "high_risk_question_count": payload.get("quality_summary", {}).get("high_risk_question_count", 0),
                "blocking_errors": blocking_errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.qa_gate and blocking_errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
