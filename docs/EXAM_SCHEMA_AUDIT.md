# Exam Schema Audit: Raw vs Processed (2021–2023)

## Summary


| Year | Raw Source        | Processed        | Options Text        | Options Graphics                                         | Answer Field                        |
| ---- | ----------------- | ---------------- | ------------------- | -------------------------------------------------------- | ----------------------------------- |
| 2020 | exams_data (dict) | processed (dict) | Preserved           | Preserved                                                | `answer`                            |
| 2021 | exams_data (list) | processed (dict) | **Lost** (90 blank) | **Lost** (45→0)                                          | `correct_answer`→missing            |
| 2022 | exams_data (list) | processed (dict) | **Lost** (65→0)     | **Lost** (`diagram_svg` 25→0)                            | `answer.correct_option`→wrong shape |
| 2023 | exams_data (list) | processed (dict) | **Lost** (55→0)     | **Lost** (35 in options + 35 in topic pool→0 in options) | `correct_option`→missing            |


## 2021

- **Raw** (`exams_data/Exam_2021.json`): `options` is list, each item has `label`, `text`, `graphics[]` with `svg_code`. `correct_answer`.
- **Processed**: `options` converted to dict `{A,B,C,D,E}` but `text` and `graphics` are empty. Stem graphics kept in `stem_graphics[].svg_code`.
- **Loss**: 45 option graphics, 90 option texts.

## 2022

- **Raw**: `options` is list, each item has `label`, `text`, `diagram_svg` (no `graphics[]`). `answer` is `{correct_option: "X"}`.
- **Processed**: `options` dict with empty `graphics[]`; `diagram_svg` never copied. `answer` kept as object, not flattened.
- **Loss**: 25 `diagram_svg` strings, 65 option texts.

## 2023

- **Raw**: `options` is list with `key` (not `label`), `text`, `graphics[]`. Topic-level `graphics[]` has `role`/`option_key` for stem vs option.
- **Processed**: `options` dict with empty `graphics[]`; topic-level `graphics[]` kept but not distributed to options.
- **Loss**: Option texts, option-level graphics; topic-level option graphics not assigned to options.

