#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.unified_review import create_unified_review_app
from kangaroo_pdf.workspace_paths import workspace_paths


def main() -> None:
    paths = workspace_paths(ROOT)
    parser = argparse.ArgumentParser(description="Run the unified PDF/text/image review tool.")
    parser.add_argument("--data-dir", default=str(paths.data_dir))
    parser.add_argument("--review-dir", default=str(paths.review_dir))
    parser.add_argument("--release-dir", default=str(paths.release_dir))
    parser.add_argument("--cache-dir", default=str(paths.cache_dir))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8012)
    args = parser.parse_args()

    app = create_unified_review_app(
        data_dir=Path(args.data_dir),
        review_dir=Path(args.review_dir),
        release_dir=Path(args.release_dir) if Path(args.release_dir).exists() else None,
        cache_dir=Path(args.cache_dir),
    )
    with make_server(args.host, args.port, app) as server:
        print(f"Unified review tool listening at http://{args.host}:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
