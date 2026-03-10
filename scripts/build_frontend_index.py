#!/usr/bin/env python3
"""
Build frontend index files from processed data:
- questions_index.json: unified question list for frontend
- question_validation.json: per-question validation status
- question_tags.json: template for difficulty/topic tags (initialized empty)
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT_ROOT / "processed"


def extract_year(paper_id: str) -> int | None:
    m = re.search(r"(\d{4})", paper_id)
    return int(m.group(1)) if m else None


def build_questions_index(index_data: dict, validation_data: dict) -> list[dict]:
    questions = []

    for exam in index_data.get("exams", []):
        path = exam["path"]
        paper_id = exam["paper_id"]
        year = extract_year(paper_id)
        full_path = PROCESSED / path

        if not full_path.exists():
            continue

        with open(full_path, encoding="utf-8") as f:
            data = json.load(f)

        for q in data.get("questions", []):
            qid = q.get("id")
            stem_graphics = q.get("stem_graphics") or []
            opts = q.get("options") or {}
            opt_graphics_count = sum(
                len(opts.get(k, {}).get("graphics") or [])
                for k in ("A", "B", "C", "D", "E")
            )
            total_graphics = len(stem_graphics) + opt_graphics_count
            answer = q.get("answer")
            valid_answer = answer in ("A", "B", "C", "D", "E") if answer else False

            id_global = f"{paper_id}_Q{qid:02d}" if qid is not None else f"{paper_id}_Q{len(questions)+1:02d}"

            questions.append({
                "id_global": id_global,
                "source_type": "exam",
                "source_id": paper_id,
                "local_id": qid,
                "display_id": f"Q{qid}" if qid is not None else f"Q{len(questions)+1}",
                "points": q.get("points"),
                "category": None,
                "year": year,
                "score_group": q.get("score_group"),
                "path": path,
                "has_answer": valid_answer,
                "has_graphics": total_graphics > 0,
                "has_formula": False,
                "graphics_count": total_graphics,
                "formula_preview": None,
            })

    for practice in index_data.get("practice", []):
        path = practice["path"]
        pid = practice["id"]
        category = practice.get("category")
        full_path = PROCESSED / path

        if not full_path.exists():
            continue

        with open(full_path, encoding="utf-8") as f:
            q = json.load(f)

        formula_latex = q.get("formula_latex") or []
        graphics = q.get("graphics") or {}
        svg_elems = graphics.get("svg_elements") if isinstance(graphics, dict) else []
        if not isinstance(svg_elems, list):
            svg_elems = []
        answer = q.get("answer")
        valid_answer = answer in ("A", "B", "C", "D", "E") if answer else False

        questions.append({
            "id_global": pid,
            "source_type": "practice",
            "source_id": pid,
            "local_id": q.get("question_number", "Q1"),
            "display_id": q.get("question_number") or pid,
            "points": q.get("points"),
            "category": category,
            "year": None,
            "score_group": None,
            "path": path,
            "has_answer": valid_answer,
            "has_graphics": len(svg_elems) > 0,
            "has_formula": len(formula_latex) > 0,
            "graphics_count": len(svg_elems),
            "formula_preview": formula_latex[0] if formula_latex else None,
        })

    return questions


def parse_validation_message(msg: str) -> tuple[str | None, str]:
    """Extract question id and error code from validation message."""
    if "question_id=" in msg:
        m = re.match(r"question_id=(\d+):\s*(.+)", msg)
        if m:
            return m.group(1), m.group(2).strip()
    if ":" in msg:
        part = msg.split(":", 1)
        if len(part) == 2:
            return part[0].strip(), part[1].strip()
    return None, msg


def map_message_to_code(msg: str) -> str:
    msg_lower = msg.lower()
    if "options is not an object" in msg_lower or "options is not a list" in msg_lower:
        return "OPTIONS_INVALID"
    if "answer" in msg_lower and "not in a–e" in msg_lower:
        return "ANSWER_INVALID"
    if "missing answer" in msg_lower:
        return "MISSING_ANSWER"
    if "added missing option" in msg_lower:
        return "ADDED_MISSING_OPTION"
    if "invalid option labels" in msg_lower:
        return "INVALID_OPTION_LABELS"
    if "graphics" in msg_lower and "not" in msg_lower:
        return "GRAPHICS_INVALID"
    return "OTHER"


def build_question_validation(
    validation_data: dict, index_data: dict
) -> dict[str, dict]:
    result = {}

    for vtype in ("exams", "practice"):
        section = validation_data.get(vtype) or {}
        for filename, info in section.items():
            errors = info.get("errors") or []
            warnings = info.get("warnings") or []
            source_id = filename.replace(".json", "")

            for msg in errors:
                qid_part, text = parse_validation_message(msg)
                code = map_message_to_code(text)
                if vtype == "exams" and qid_part:
                    id_global = f"{source_id}_Q{int(qid_part):02d}"
                elif vtype == "practice":
                    id_global = source_id
                else:
                    continue
                if id_global not in result:
                    result[id_global] = {"level": "error", "codes": []}
                if code not in result[id_global]["codes"]:
                    result[id_global]["codes"].append(code)

            for msg in warnings:
                qid_part, text = parse_validation_message(msg)
                code = map_message_to_code(text)
                if vtype == "exams" and qid_part:
                    id_global = f"{source_id}_Q{int(qid_part):02d}"
                elif vtype == "practice":
                    id_global = source_id
                else:
                    continue
                if id_global not in result:
                    result[id_global] = {"level": "warning", "codes": []}
                elif result[id_global]["level"] == "error":
                    continue
                if code not in result[id_global]["codes"]:
                    result[id_global]["codes"].append(code)

    return result


def fix_exam_source_id(filename: str) -> str:
    if "Exam_" in filename:
        return filename.replace(".json", "")
    return filename.replace(".json", "")


def main():
    index_path = PROCESSED / "index.json"
    validation_path = PROCESSED / "validation_report.json"

    with open(index_path, encoding="utf-8") as f:
        index_data = json.load(f)

    with open(validation_path, encoding="utf-8") as f:
        validation_data = json.load(f)

    questions = build_questions_index(index_data, validation_data)
    with open(PROCESSED / "questions_index.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    question_validation = build_question_validation(validation_data, index_data)
    with open(PROCESSED / "question_validation.json", "w", encoding="utf-8") as f:
        json.dump(question_validation, f, ensure_ascii=False, indent=2)

    question_tags_path = PROCESSED / "question_tags.json"
    if not question_tags_path.exists():
        tags = {}
        for q in questions:
            topic_tags = [q["category"]] if q.get("category") else []
            tags[q["id_global"]] = {
                "difficulty": None,
                "topic_tags": topic_tags,
                "age_group": None,
            }
        with open(question_tags_path, "w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(questions)} questions to questions_index.json")
    print(f"Wrote {len(question_validation)} validation entries to question_validation.json")
    print(f"Initialized question_tags.json")


if __name__ == "__main__":
    main()
