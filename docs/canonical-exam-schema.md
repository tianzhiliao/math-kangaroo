# Canonical Exam Question Schema

This document describes the committed exam JSON shape stored in the repository, plus the frontend-only runtime enrichments added after load time.

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

## Frontend Runtime-Enriched Fields

The committed exam JSON files on disk do not include the fields below. The frontend adds them at runtime when it builds `Practice_Bank` from the committed exam papers.

| Field | Type | Description |
|-------|------|-------------|
| `practiceQuestionId` | number | Stable session ID assigned by the frontend for practice-mode questions |
| `sourceRef` | object | `{ examId, questionId, questionNumber }` pointing back to the original committed paper question |

### `sourceRef` Shape

| Field | Type | Description |
|-------|------|-------------|
| `examId` | string | Original paper ID, for example `Exam_2021` |
| `questionId` | number | Original committed question ID inside that paper |
| `questionNumber` | number | Original display order within that paper |

## Notes

- Practice mode is built by combining the committed exam papers at runtime; it does not use a separate committed practice JSON schema in the running app.
- `practiceQuestionId` is used for stable practice-session identity, while `sourceRef` is used for source labels and for routing stem-audio playback back to the original paper question.
- The backend reads the same exam files by default through `EXAM_DATA_DIR=frontend/public/data`.
