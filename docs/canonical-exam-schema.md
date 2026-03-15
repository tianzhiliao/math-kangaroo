# Canonical Exam Question Schema

This document describes the committed runtime JSON shape used by the frontend and backend exam features.

Runtime exam files live under `frontend/public/data/Exam_20xx.json`.

## Paper Level

```json
{
  "paper_id": "Exam_2020",
  "questions": [...]
}
```

## Question Level (Canonical)

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Question ID |
| `stem_text` | string | Stem/body text |
| `stem_graphics` | array | `[{ id, svg_path }]` — stem SVG file references |
| `options` | object | `{ A: { text, graphics }, B: {...}, ... }` |
| `answer` | string | "A" \| "B" \| "C" \| "D" \| "E" |
| `points` | number | Score |
| `score_group` | string \| null | Part (A/B/C) |
| `sourceSchema` | string | "exam2020" \| "exam2021" \| "exam2022" \| "exam2023" |

## Example Question

```json
{
  "id": 1,
  "stem_text": "Which number is the largest?",
  "stem_graphics": [
    {
      "id": "q01_stem_01",
      "svg_path": "svg/Exam_2020/q01_stem_01.svg"
    }
  ],
  "options": {
    "A": { "text": "12", "graphics": [] },
    "B": { "text": "21", "graphics": [] },
    "C": { "text": "102", "graphics": [] },
    "D": { "text": "99", "graphics": [] },
    "E": { "text": "89", "graphics": [] }
  },
  "answer": "C",
  "points": 3,
  "score_group": "A",
  "sourceSchema": "exam2020"
}
```

## Option Level

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Option text |
| `graphics` | array | `[{ id, svg_path }]` — option SVG file references |

## Graphics Item

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | graphic_id or diagram_id |
| `svg_path` | string | Relative SVG file path, e.g. `svg/Exam_2020/q01_stem_1.svg` |

## Runtime Expectations

- 5 options (A–E) present
- `answer` in A–E
- Each option should have `text`, `graphics`, or both
- `svg_path` values are resolved by the frontend relative to the JSON file URL
- Both frontend and backend assume `paper_id` matches the JSON filename stem, for example `Exam_2020`

## Notes

- Practice mode is built by combining the committed exam papers at runtime; it does not use a separate practice JSON schema in the running app.
- The backend reads the same exam files by default through `EXAM_DATA_DIR=frontend/public/data`.
