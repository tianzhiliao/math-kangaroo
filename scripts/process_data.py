import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
EXAMS_DIR = ROOT / "exams_data"
PRACTICE_DIR = ROOT / "practice_data"
OUTPUT_ROOT = ROOT / "processed"
OUTPUT_EXAMS = OUTPUT_ROOT / "exams"
OUTPUT_PRACTICE = OUTPUT_ROOT / "practice"


def ensure_output_dirs() -> None:
    OUTPUT_EXAMS.mkdir(parents=True, exist_ok=True)
    OUTPUT_PRACTICE.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def clean_exam_file(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    exam = load_json(path)
    report: Dict[str, Any] = {"errors": [], "warnings": []}

    questions = exam.get("questions", [])
    seen_ids = set()

    for q in questions:
        qid = q.get("id")
        label = f"question_id={qid}"

        if qid in seen_ids:
            report["errors"].append(f"{label}: duplicate id")
        else:
            seen_ids.add(qid)

        stem_text = q.get("stem_text")
        if not isinstance(stem_text, str) or not stem_text.strip():
            report["errors"].append(f"{label}: missing or empty stem_text")

        options = q.get("options")
        if not isinstance(options, dict):
            report["errors"].append(f"{label}: options is not an object")
            options = {}
            q["options"] = options

        for opt_label in ("A", "B", "C", "D", "E"):
            if opt_label not in options:
                options[opt_label] = {"text": "", "graphics": []}
                report["warnings"].append(
                    f"{label}: added missing option {opt_label}"
                )

        answer = q.get("answer")
        if answer is None or answer == "":
            report["warnings"].append(f"{label}: missing answer")
        elif answer not in ("A", "B", "C", "D", "E"):
            report["errors"].append(
                f"{label}: answer '{answer}' not in A–E"
            )

    return exam, report


def fix_points_and_placeholder(question: Dict[str, Any]) -> None:
    """
    Ensure points is an int and, if question_text contains a '( points for the correct answer)'
    placeholder, fill it with the numeric value.
    """
    points = question.get("points")
    if points is None:
        # 默认 3 分，如果将来有更复杂规则可以在此调整
        points = 3
        question["points"] = points

    text = question.get("question_text")
    if isinstance(text, str):
        placeholder = "( points for the correct answer)"
        if placeholder in text:
            filled = text.replace(placeholder, f"({points} points for the correct answer)")
            question["question_text"] = filled


def clean_practice_file(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    q = load_json(path)
    report: Dict[str, Any] = {"errors": [], "warnings": []}

    qid = q.get("id", path.stem)

    # 必填字段
    if not isinstance(qid, str) or not qid:
        report["errors"].append(f"{path.name}: missing id")
    if not isinstance(q.get("question_text"), str) or not q["question_text"].strip():
        report["errors"].append(f"{qid}: missing or empty question_text")

    # points & 占位符修复
    fix_points_and_placeholder(q)

    # formula_latex 统一为数组
    formula = q.get("formula_latex")
    if formula is None:
        q["formula_latex"] = []
    elif not isinstance(formula, list):
        q["formula_latex"] = [str(formula)]

    # options 校验
    options = q.get("options")
    if not isinstance(options, list):
        report["errors"].append(f"{qid}: options is not a list")
        options = []
        q["options"] = options

    if len(options) != 5:
        report["warnings"].append(
            f"{qid}: expected 5 options, found {len(options)}"
        )

    valid_labels = ("A", "B", "C", "D", "E")
    labels = [opt.get("label") for opt in options if isinstance(opt, dict)]
    if any(lbl not in valid_labels for lbl in labels):
        report["errors"].append(f"{qid}: invalid option labels {labels}")

    # answer 合法性
    answer = q.get("answer")
    if answer is None or answer == "":
        report["warnings"].append(f"{qid}: missing answer")
    elif answer not in valid_labels:
        report["errors"].append(
            f"{qid}: answer '{answer}' not in A–E"
        )

    # graphics 结构检查
    graphics = q.get("graphics")
    if graphics is not None and not isinstance(graphics, dict):
        report["warnings"].append(f"{qid}: graphics is not an object")
    elif isinstance(graphics, dict):
        svg_elements = graphics.get("svg_elements")
        if svg_elements is not None and not isinstance(svg_elements, list):
            report["warnings"].append(
                f"{qid}: graphics.svg_elements is not a list"
            )

    return q, report


def process_all() -> None:
    ensure_output_dirs()

    validation_report: Dict[str, Any] = {"exams": {}, "practice": {}}
    index: Dict[str, Any] = {"exams": [], "practice": [], "categories": set()}

    # 处理 exams_data
    if EXAMS_DIR.exists():
        for path in sorted(EXAMS_DIR.glob("*.json")):
            cleaned, report = clean_exam_file(path)
            out_path = OUTPUT_EXAMS / path.name
            dump_json(cleaned, out_path)

            paper_id = cleaned.get("paper_id", path.stem)
            questions = cleaned.get("questions", [])
            index["exams"].append(
                {
                    "paper_id": paper_id,
                    "question_count": len(questions),
                    "path": f"exams/{path.name}",
                }
            )
            validation_report["exams"][path.name] = report

    # 处理 practice_data
    seen_practice_ids: set = set()
    if PRACTICE_DIR.exists():
        for path in sorted(PRACTICE_DIR.glob("*.json")):
            cleaned, report = clean_practice_file(path)
            out_path = OUTPUT_PRACTICE / path.name
            dump_json(cleaned, out_path)

            pid = cleaned.get("id", path.stem)
            if pid in seen_practice_ids:
                report["errors"].append(f"{pid}: duplicate id across practice files")
            else:
                seen_practice_ids.add(pid)

            category = cleaned.get("category")
            if isinstance(category, str) and category:
                index["categories"].add(category)

            index["practice"].append(
                {
                    "id": pid,
                    "category": category,
                    "path": f"practice/{path.name}",
                }
            )
            validation_report["practice"][path.name] = report

    # 将 categories 从集合转换为排序后的列表
    index["categories"] = sorted(index["categories"])

    dump_json(index, OUTPUT_ROOT / "index.json")
    dump_json(validation_report, OUTPUT_ROOT / "validation_report.json")


if __name__ == "__main__":
    process_all()

