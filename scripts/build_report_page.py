#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.report_page import build_report_page


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a non-technical HTML summary page for the current PDF extraction results.")
    parser.add_argument("--data-dir", default=str(ROOT / "data"))
    parser.add_argument("--output", default=str(ROOT / "reports" / "codex-work-summary.html"))
    args = parser.parse_args()
    build_report_page(args.data_dir, args.output)


if __name__ == "__main__":
    main()
