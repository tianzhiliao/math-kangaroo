#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.pipeline import build_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Build structured Math Kangaroo exam JSON from source PDFs.")
    parser.add_argument("--source-dir", default=str(ROOT / "original_pdf_data"))
    parser.add_argument("--output-dir", default=str(ROOT / "data"))
    args = parser.parse_args()
    build_dataset(Path(args.source_dir), Path(args.output_dir))


if __name__ == "__main__":
    main()
