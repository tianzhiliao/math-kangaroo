# Canonical Exam Question Schema

Frontend and index scripts consume this unified structure. All year-specific adapters output this format.

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

## Validation Rules

- 5 options (A–E) present
- `answer` in A–E
- Each option has `text` or `graphics` (or both) non-empty
- `graphics_count` = stem_graphics.length + sum(option.graphics.length)

## Year Adapters (scripts/normalize_exams_to_canonical.py)

| Year | Input | Stem Graphics | Option Graphics | Answer |
|------|-------|---------------|-----------------|--------|
| 2020 | exams_data, options dict | stem_graphics[].svg | options.*.graphics[].svg | answer |
| 2021 | exams_data, options list | stem_graphics[].svg_code | options[].graphics[].svg_code | correct_answer |
| 2022 | exams_data, options list | stem_diagrams[].svg | options[].diagram_svg | answer.correct_option |
| 2023 | exams_data, options list | topic graphics[] role=stem | topic graphics[] role=option + option_key; options[].graphics[] (IDs) | correct_option |
