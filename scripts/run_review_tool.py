#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.review_tool import create_review_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local review tool for exam QA.")
    parser.add_argument("--data-dir", default=str(ROOT / "data"))
    parser.add_argument("--review-dir", default=str(ROOT / "review-data"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8012)
    args = parser.parse_args()

    app = create_review_app(Path(args.data_dir), Path(args.review_dir))
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
