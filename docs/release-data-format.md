# Release-Data Format

`release-data/` is the runtime content contract for this repository.

Both the Next.js app and the FastAPI service read from it directly.

## Directory layout

```text
release-data/
|-- manifest.json
`-- exams/
    `-- <exam_id>/
        |-- exam.json
        `-- assets/
            `-- ...
```

## Top-level manifest

Path:

```text
release-data/manifest.json
```

Current top-level keys:

- `schema_version`
- `generated_at`
- `exams`

Each `exams[]` entry currently contains:

- `asset_count`
- `exam_id`
- `family`
- `language`
- `level`
- `path`
- `question_count`
- `year`

Example shape:

```json
{
  "schema_version": 1,
  "generated_at": "2026-03-19T00:00:00+00:00",
  "exams": [
    {
      "exam_id": "felix-austria-2014",
      "path": "exams/felix-austria-2014/exam.json",
      "family": "felix_austria_15",
      "year": 2014,
      "level": "felix",
      "language": "en",
      "question_count": 15,
      "asset_count": 5
    }
  ]
}
```

## Exam payload

Path:

```text
release-data/exams/<exam_id>/exam.json
```

Current top-level keys:

- `answer_key`
- `assets`
- `duration_minutes`
- `exam_id`
- `family`
- `instructions`
- `language`
- `level`
- `question_count`
- `questions`
- `scoring_rules`
- `year`

## `scoring_rules`

Each scoring rule has:

- `from`
- `to`
- `points`

## `assets`

Each asset record currently contains:

- `format`
- `height`
- `id`
- `kind`
- `media_type`
- `path`
- `role`
- `width`

Example:

```json
{
  "id": "q01_stem_01",
  "path": "assets/q01_stem_01.png",
  "format": "png",
  "media_type": "image/png",
  "kind": "question_figure",
  "role": "stem",
  "width": 80,
  "height": 40
}
```

## `questions`

Each question currently contains:

- `choices`
- `id`
- `number`
- `part`
- `points`
- `shared_asset_refs`
- `stem_text`

### `choices`

Each choice currently contains:

- `asset_refs`
- `label`
- `text`

Example question shape:

```json
{
  "id": "q01",
  "number": 1,
  "part": "part_a",
  "points": 3,
  "stem_text": "Which figure is shaded?",
  "shared_asset_refs": ["q01_stem_01"],
  "choices": [
    {
      "label": "A",
      "text": "Triangle",
      "asset_refs": []
    }
  ]
}
```

## Asset path resolution

Asset paths inside `exam.json` are relative to the exam directory.

Example:

- exam directory: `release-data/exams/felix-austria-2014/`
- asset path in JSON: `assets/q01_stem_01.png`
- real file path: `release-data/exams/felix-austria-2014/assets/q01_stem_01.png`

The web app serves these files through:

- `/api/exams/[examId]/raw/[...path]`

## Stability expectations

`release-data/` is the closest thing this repository has to a public runtime schema.

If you change:

- manifest keys
- exam payload keys
- asset path semantics
- question/choice field names

then you should update:

- `docs/release-data-format.md`
- `docs/api.md`
- any affected UI or API code

## Current consumers

### Next.js

The web layer reads:

- `manifest.json` through `/api/exams`
- `exam.json` through `/api/exams/[examId]`
- raw assets through `/api/exams/[examId]/raw/[...path]`

### FastAPI

The API layer reads:

- manifest data through `/manifest`
- exam data through `/exams/{exam_id}`
- question-level content for AI explanation and TTS lookup

## Design intent

The release dataset intentionally excludes internal workflow data such as:

- source PDF paths in the runtime artifact
- review-only references
- HTML reports
- legacy extraction bookkeeping

That keeps the runtime interface compact and deployable.
