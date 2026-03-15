#!/usr/bin/env python3
"""
Normalize exam JSON from raw (exams_data) to canonical schema for frontend.
Output: processed/exams/Exam_20xx.json
"""

import json
import hashlib
import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMS_DATA = PROJECT_ROOT / "exams_data"
PROCESSED_EXAMS = PROJECT_ROOT / "processed" / "exams"
PROCESSED_EXAM_SVG = PROCESSED_EXAMS / "svg"
FRONTEND_PUBLIC_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
FRONTEND_EXAM_SVG = FRONTEND_PUBLIC_DATA / "svg"


SVG_ID_RE = re.compile(r'\bid=(["\'])([^"\']+)\1')
SVG_URL_REF_RE = re.compile(r"url\(#([^)]+)\)")
SVG_HREF_RE = re.compile(r'((?:xlink:)?href)=(["\'])#([^"\']+)\2')
GRAPHIC_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "").strip("_")
    return token or "graphic"


def _namespace_svg_ids(svg: str, namespace: str) -> str:
    """Rewrite internal SVG ids so multiple inline SVGs can coexist safely."""
    if not svg or "id=" not in svg:
        return svg

    mapping = {}
    prefix = f"svg_{_safe_token(namespace)}"

    def replace_id(match: re.Match) -> str:
        quote = match.group(1)
        old_id = match.group(2)
        new_id = mapping.setdefault(old_id, f"{prefix}__{old_id}")
        return f'id={quote}{new_id}{quote}'

    svg = SVG_ID_RE.sub(replace_id, svg)
    if not mapping:
        return svg

    svg = SVG_URL_REF_RE.sub(
        lambda m: f"url(#{mapping.get(m.group(1), m.group(1))})",
        svg,
    )
    svg = SVG_HREF_RE.sub(
        lambda m: f'{m.group(1)}={m.group(2)}#{mapping.get(m.group(3), m.group(3))}{m.group(2)}',
        svg,
    )
    return svg


def _dedupe_graphics(graphics: list) -> list:
    items = []
    seen = set()
    for g in graphics:
        if not g:
            continue
        key = (g.get("id") or "", g.get("svg_path") or g.get("svg") or "")
        if key in seen:
            continue
        seen.add(key)
        items.append(g)
    return items


def _validate_graphic_id(graph_id: str) -> str:
    if not GRAPHIC_ID_RE.fullmatch(graph_id):
        raise ValueError(f"Graphic id '{graph_id}' is not safe to use as a file name")
    return graph_id


def _graph(id_: str, svg: str, paper_id: str, svg_root: Path) -> dict:
    if not (svg and isinstance(svg, str) and svg.strip()):
        return None
    graph_id = id_ or f"anon_{hashlib.md5(svg.encode('utf-8')).hexdigest()[:12]}"
    graph_id = _validate_graphic_id(graph_id)
    namespaced_svg = _namespace_svg_ids(svg, graph_id)
    paper_dir = svg_root / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    svg_file = paper_dir / f"{graph_id}.svg"
    svg_file.write_text(namespaced_svg, encoding="utf-8")
    return {
        "id": graph_id,
        "svg_path": (Path("svg") / paper_id / svg_file.name).as_posix(),
    }


def _option(label: str, text: str, graphics: list) -> dict:
    items = _dedupe_graphics(graphics)
    return {"text": text or "", "graphics": items}


def adapter_2020(data: dict, svg_root: Path) -> dict:
    """2020: options already dict, stem_graphics[].svg, options.*.graphics[].svg, answer."""
    paper_id = data.get("paper_id", "Exam_2020")
    out = {"paper_id": paper_id, "questions": []}
    for q in data.get("questions", []):
        stem = []
        for g in q.get("stem_graphics") or []:
            svg = g.get("svg") or g.get("svg_code")
            if svg:
                stem.append(_graph(g.get("graphic_id", ""), svg, paper_id, svg_root))
        opts = {}
        raw_opts = q.get("options") or {}
        for k in ["A", "B", "C", "D", "E"]:
            o = raw_opts.get(k) or {}
            gs = []
            for g in o.get("graphics") or []:
                svg = g.get("svg") or g.get("svg_code")
                if svg:
                    gs.append(_graph(g.get("graphic_id", ""), svg, paper_id, svg_root))
            opts[k] = _option(k, o.get("text") or "", gs)
        answer = q.get("answer")
        if isinstance(answer, dict):
            answer = answer.get("correct_option") or answer.get("correct_answer") or ""
        out["questions"].append({
            "id": q.get("id"),
            "stem_text": q.get("stem_text") or "",
            "stem_graphics": stem,
            "options": opts,
            "answer": answer if answer in ("A", "B", "C", "D", "E") else "",
            "points": q.get("points"),
            "score_group": q.get("score_group"),
            "sourceSchema": "exam2020",
        })
    return out


def adapter_2021(data: dict, svg_root: Path) -> dict:
    """2021: options list with label/text/graphics[].svg_code, stem_graphics[].svg_code, correct_answer."""
    paper_id = data.get("paper_id", "Exam_2021")
    out = {"paper_id": paper_id, "questions": []}
    for q in data.get("questions", []):
        stem = []
        for g in q.get("stem_graphics") or []:
            svg = g.get("svg") or g.get("svg_code")
            if svg:
                stem.append(_graph(g.get("graphic_id", ""), svg, paper_id, svg_root))
        opts = {}
        raw_opts = q.get("options") or []
        label_map = {}
        for o in raw_opts if isinstance(raw_opts, list) else []:
            lab = o.get("label") or o.get("key") or ""
            label_map[lab] = o
        for k in ["A", "B", "C", "D", "E"]:
            o = label_map.get(k) or {}
            gs = []
            for g in o.get("graphics") or []:
                svg = g.get("svg") or g.get("svg_code")
                if svg:
                    gs.append(_graph(g.get("graphic_id", ""), svg, paper_id, svg_root))
            opts[k] = _option(k, o.get("text") or "", gs)
        answer = q.get("correct_answer") or q.get("answer") or ""
        if isinstance(answer, dict):
            answer = answer.get("correct_option") or ""
        out["questions"].append({
            "id": q.get("id"),
            "stem_text": q.get("stem_text") or "",
            "stem_graphics": stem,
            "options": opts,
            "answer": answer if answer in ("A", "B", "C", "D", "E") else "",
            "points": q.get("points"),
            "score_group": q.get("score_group"),
            "sourceSchema": "exam2021",
        })
    return out


def adapter_2022(data: dict, svg_root: Path) -> dict:
    """2022: options list with diagram_svg, stem_diagrams[].svg, answer.correct_option."""
    paper_id = data.get("paper_id", "Exam_2022")
    out = {"paper_id": paper_id, "questions": []}
    for q in data.get("questions", []):
        stem = []
        for g in q.get("stem_diagrams") or []:
            svg = g.get("svg") or g.get("svg_code")
            if svg:
                stem.append(_graph(g.get("diagram_id", ""), svg, paper_id, svg_root))
        opts = {}
        raw_opts = q.get("options") or []
        label_map = {}
        for o in raw_opts if isinstance(raw_opts, list) else []:
            lab = o.get("label") or o.get("key") or ""
            label_map[lab] = o
        for k in ["A", "B", "C", "D", "E"]:
            o = label_map.get(k) or {}
            gs = []
            ds = o.get("diagram_svg")
            if ds:
                gs.append(_graph(o.get("diagram_id") or f"q{q.get('id')}_opt_{k}", ds, paper_id, svg_root))
            for g in o.get("graphics") or []:
                svg = g.get("svg") or g.get("svg_code")
                if svg:
                    gs.append(_graph(g.get("graphic_id", ""), svg, paper_id, svg_root))
            opts[k] = _option(k, o.get("text") or "", gs)
        answer = q.get("answer")
        if isinstance(answer, dict):
            answer = answer.get("correct_option") or ""
        else:
            answer = answer or ""
        out["questions"].append({
            "id": q.get("id"),
            "stem_text": q.get("stem_text") or "",
            "stem_graphics": stem,
            "options": opts,
            "answer": answer if answer in ("A", "B", "C", "D", "E") else "",
            "points": q.get("points"),
            "score_group": q.get("score_group"),
            "sourceSchema": "exam2022",
        })
    return out


def adapter_2023(data: dict, svg_root: Path) -> dict:
    """2023: options list with key/text/graphics[] (IDs); topic-level graphics[] with role/option_key."""
    paper_id = data.get("paper_id", "Exam_2023")
    out = {"paper_id": paper_id, "questions": []}
    for q in data.get("questions", []):
        topic_graphics = q.get("graphics") or []
        id_to_graph = {}
        for g in topic_graphics:
            if isinstance(g, dict):
                gid = g.get("graphic_id")
                if gid:
                    id_to_graph[gid] = g
        stem = []
        opt_graphics = {"A": [], "B": [], "C": [], "D": [], "E": []}
        for g in topic_graphics:
            if not isinstance(g, dict):
                continue
            svg = g.get("svg") or g.get("svg_code")
            if not svg:
                continue
            item = _graph(g.get("graphic_id", ""), svg, paper_id, svg_root)
            if not item:
                continue
            role = g.get("role")
            key = g.get("option_key")
            if role == "stem" or key is None:
                stem.append(item)
            elif role == "option" and key in opt_graphics:
                opt_graphics[key].append(item)
        opts = {}
        raw_opts = q.get("options") or []
        label_map = {}
        for o in raw_opts if isinstance(raw_opts, list) else []:
            lab = o.get("label") or o.get("key") or ""
            label_map[lab] = o
        for k in ["A", "B", "C", "D", "E"]:
            o = label_map.get(k) or {}
            gs = list(opt_graphics.get(k) or [])
            for g in o.get("graphics") or []:
                if isinstance(g, str):
                    ref = id_to_graph.get(g)
                    if ref:
                        svg = ref.get("svg") or ref.get("svg_code")
                        if svg:
                            it = _graph(ref.get("graphic_id", g), svg, paper_id, svg_root)
                            if it:
                                gs.append(it)
                elif isinstance(g, dict):
                    svg = g.get("svg") or g.get("svg_code")
                    if svg:
                        it = _graph(g.get("graphic_id", ""), svg, paper_id, svg_root)
                        if it:
                            gs.append(it)
            opts[k] = _option(k, o.get("text") or "", gs)
        answer = q.get("correct_option") or q.get("answer") or ""
        if isinstance(answer, dict):
            answer = answer.get("correct_option") or ""
        out["questions"].append({
            "id": q.get("id"),
            "stem_text": q.get("stem_text") or "",
            "stem_graphics": stem,
            "options": opts,
            "answer": answer if answer in ("A", "B", "C", "D", "E") else "",
            "points": q.get("points"),
            "score_group": q.get("score_group"),
            "sourceSchema": "exam2023",
        })
    return out


ADAPTERS = {
    2020: adapter_2020,
    2021: adapter_2021,
    2022: adapter_2022,
    2023: adapter_2023,
}


def validate_canonical(out: dict) -> list[str]:
    """Return list of validation errors (blocking)."""
    errs = []
    for q in out.get("questions", []):
        qid = q.get("id")
        opts = q.get("options") or {}
        for k in ("A", "B", "C", "D", "E"):
            if k not in opts:
                errs.append(f"Q{qid}: missing option {k}")
        ans = q.get("answer")
        if ans and ans not in ("A", "B", "C", "D", "E"):
            errs.append(f"Q{qid}: answer '{ans}' not in A-E")
    return errs


def sync_exam_to_frontend(paper_id: str, exam_json: Path) -> None:
    FRONTEND_PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exam_json, FRONTEND_PUBLIC_DATA / exam_json.name)

    src_svg_dir = PROCESSED_EXAM_SVG / paper_id
    dst_svg_dir = FRONTEND_EXAM_SVG / paper_id
    if dst_svg_dir.exists():
        shutil.rmtree(dst_svg_dir)
    if src_svg_dir.exists():
        dst_svg_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_svg_dir, dst_svg_dir)


def main():
    PROCESSED_EXAMS.mkdir(parents=True, exist_ok=True)
    PROCESSED_EXAM_SVG.mkdir(parents=True, exist_ok=True)
    FRONTEND_PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    FRONTEND_EXAM_SVG.mkdir(parents=True, exist_ok=True)

    for year, adapter in ADAPTERS.items():
        src = EXAMS_DATA / f"Exam_{year}.json"
        if not src.exists():
            print(f"Skip {year}: {src} not found")
            continue
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
        paper_id = data.get("paper_id", f"Exam_{year}")

        processed_svg_dir = PROCESSED_EXAM_SVG / paper_id
        if processed_svg_dir.exists():
            shutil.rmtree(processed_svg_dir)

        out = adapter(data, PROCESSED_EXAM_SVG)
        errs = validate_canonical(out)
        if errs:
            for e in errs[:10]:
                print(f"  {e}")
            if len(errs) > 10:
                print(f"  ... and {len(errs) - 10} more")
        dst = PROCESSED_EXAMS / f"Exam_{year}.json"
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        sync_exam_to_frontend(paper_id, dst)
        print(f"Wrote {dst}")


if __name__ == "__main__":
    main()
