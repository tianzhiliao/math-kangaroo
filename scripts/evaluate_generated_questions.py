#!/usr/bin/env python3
"""Evaluate the AI-generated similar questions under generated/.

Structural audit (free, offline):

    python3 scripts/evaluate_generated_questions.py

Add an independent solve, where a vision model answers each variant from its
card image without seeing the key, and disagreements are listed for review:

    python3 scripts/evaluate_generated_questions.py --solve

Solve results are cached per question in --solve-cache, keyed by the model and
a digest of question.json and card.png, so reruns only pay for changed items.
Exits non-zero when the audit has errors, or the solver disagrees with a key
or could not check an item.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kangaroo_pdf.generated_questions import (  # noqa: E402
    audit_generated_questions,
    load_release_questions,
    render_markdown,
    resolve_variant_dir,
)

SOLVE_PROMPT = """
You are checking a multiple-choice math contest question for children aged 6-8.
The image shows the whole question: the question text, the picture and the answer choices.
Solve it carefully. Look at every detail of the picture and count twice.
Return the letter of the single correct choice. If no choice is correct, or more
than one is, return "NONE" and say why.
""".strip()

SOLVE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "answer": {"type": "string", "enum": ["A", "B", "C", "D", "E", "NONE"]},
    },
    "required": ["reasoning", "answer"],
    "additionalProperties": False,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release-dir", type=Path, default=ROOT / "release-data")
    parser.add_argument("--generated-dir", type=Path, default=ROOT / "generated")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "review" / "generated-eval")
    parser.add_argument("--solve", action="store_true", help="Also solve each variant with a vision model.")
    parser.add_argument("--model", default=os.environ.get("OPENAI_EVAL_MODEL", "gpt-5.4"))
    parser.add_argument("--exam-id", dest="exam_ids", action="append", help="Limit the solve to these exams.")
    parser.add_argument("--limit", type=int, help="Solve at most this many variants.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--solve-cache", type=Path, default=ROOT / ".generated" / "cache" / "variant-solve")
    args = parser.parse_args()

    report = audit_generated_questions(args.release_dir, args.generated_dir)
    solver = None
    if args.solve:
        solver = solve_variants(args)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"audit": report.as_dict()}
    if solver is not None:
        payload["solve"] = solver
    (args.out_dir / "report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out_dir / "report.md").write_text(render_markdown(report, solver), encoding="utf-8")

    print(
        f"variants={report.variants} duplicates={report.duplicates} missing={len(report.missing)} "
        f"errors={len(report.errors)} warnings={len(report.warnings)} notes={len(report.notes)}"
    )
    unresolved = 0
    if solver is not None:
        counts = {s: sum(1 for r in solver["results"] if r["status"] == s) for s in ("agree", "disagree", "error")}
        unresolved = counts["disagree"] + counts["error"]
        print(f"solve model={solver['model']} agree={counts['agree']} disagree={counts['disagree']} error={counts['error']}")
    print(f"report: {args.out_dir / 'report.md'}")
    return 1 if report.errors or unresolved else 0


def solve_variants(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass
    from openai import OpenAI

    client = OpenAI()
    jobs: list[tuple[str, str, Path]] = []
    for exam_id, exam in load_release_questions(args.release_dir).items():
        if args.exam_ids and exam_id not in args.exam_ids:
            continue
        for question in exam["questions"]:
            # Withdrawn variants are skipped; duplicates are solved once, at their own folder.
            folder = args.generated_dir / exam_id / question["id"]
            if (folder / "question.json").is_file() and resolve_variant_dir(
                args.generated_dir, exam_id, question["id"]
            ):
                jobs.append((exam_id, question["id"], folder))
    if args.limit:
        jobs = jobs[: args.limit]

    args.solve_cache.mkdir(parents=True, exist_ok=True)

    def run(job: tuple[str, str, Path]) -> dict[str, Any]:
        exam_id, question_id, folder = job
        question = json.loads((folder / "question.json").read_text(encoding="utf-8"))
        result: dict[str, Any] = {"exam_id": exam_id, "question_id": question_id, "answer": question.get("answer")}
        card = folder / "card.png"
        if not card.is_file():
            return {**result, "status": "error", "error": "card.png missing"}
        card_bytes = card.read_bytes()
        digest = hashlib.sha256(
            args.model.encode() + (folder / "question.json").read_bytes() + card_bytes + SOLVE_PROMPT.encode()
        ).hexdigest()
        cache_file = args.solve_cache / f"{digest}.json"
        if cache_file.is_file():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            try:
                response = client.responses.create(
                    model=args.model,
                    input=[
                        {"role": "system", "content": [{"type": "input_text", "text": SOLVE_PROMPT}]},
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": f"Question text: {question.get('stem_text', '')}"},
                                {
                                    "type": "input_image",
                                    "image_url": "data:image/png;base64," + base64.b64encode(card_bytes).decode("ascii"),
                                },
                            ],
                        },
                    ],
                    text={"format": {"type": "json_schema", "name": "solve", "strict": True, "schema": SOLVE_SCHEMA}},
                )
                cached = json.loads(response.output_text)
            except Exception as exc:  # noqa: BLE001 - report and continue
                return {**result, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
            cache_file.write_text(json.dumps(cached, ensure_ascii=False) + "\n", encoding="utf-8")
        model_answer = str(cached.get("answer", "")).upper()
        status = "agree" if model_answer == str(question.get("answer", "")).upper() else "disagree"
        return {**result, "status": status, "model_answer": model_answer, "reasoning": cached.get("reasoning", "")}

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(run, jobs))
    return {"model": args.model, "results": results}


if __name__ == "__main__":
    raise SystemExit(main())
