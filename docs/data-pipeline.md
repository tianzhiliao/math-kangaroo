# Data Pipeline

This document explains the PDF/content-processing side of the repository.

## Purpose

The pipeline converts upstream Math Kangaroo PDF inputs into a runtime dataset that the web app and API can consume.

The broad stages are:

1. classify source PDFs
2. extract questions, choices, answers, and assets
3. review suspicious or low-confidence fields
4. build a PNG-only release dataset
5. validate the release output

## Main modules

### `src/kangaroo_pdf/pipeline.py`

Core extraction pipeline.

Responsibilities include:

- classifying supported PDF naming patterns
- reading text and page metadata
- detecting question sequences
- extracting structured exam content
- handling question assets and answer tables

Typical script entrypoint:

```bash
python3 scripts/build_exam_data.py
```

## `src/kangaroo_pdf/text_review_pipeline.py`

Builds structured review datasets for text-field inspection and correction workflows.

Use this area when:

- extraction quality needs review
- a question field is suspicious
- baseline text and extracted text need comparison

## `src/kangaroo_pdf/unified_review.py`

Implements the unified local review tool.

Typical script entrypoint:

```bash
python3 scripts/run_unified_review.py
```

The review tool helps inspect:

- exams
- per-question review fields
- answer fields
- rendered assets and report links

## `src/kangaroo_pdf/release_pipeline.py`

Builds and validates the runtime-facing `release-data/` package.

Responsibilities include:

- copying only referenced assets into the release output
- trimming legacy/internal fields from exam JSON
- producing the top-level manifest
- validating the final dataset shape and file types
- generating a cleanup allowlist report

Typical script entrypoint:

```bash
python3 scripts/build_release_data.py
```

## Important supporting modules

- `answer_sync.py`: answer-key synchronization helpers
- `answer_compare_report.py`: answer compare reporting
- `ab_compare.py`: A/B comparison tooling
- `asset_qa.py`: asset QA support
- `diagram_assets.py` and `visual_assets.py`: image extraction helpers
- `verified_answers.py`: verified answer-key support
- `workspace_paths.py`: canonical workspace path resolution

## Input and output boundaries

### Inputs

Common upstream or working inputs include:

- `original_pdf_data/`
- intermediate extracted data directories
- review JSON files
- generated reports

These are part of the content-production workflow, not the deployed runtime contract.

### Outputs

The important runtime output is:

- `release-data/`

This output is intentionally compact and stripped of internal-only fields. It is what the web app and FastAPI service depend on at runtime.

## What is not committed by default

Not every content-processing input is expected in a clean clone. In particular:

- full raw PDF source collections may be absent
- review artifacts may be absent
- generated pipeline caches may be absent

That is why some data-workflow tests may fail even though application runtime behavior still works with the committed `release-data/`.

## Common workflow

A typical end-to-end content refresh looks like this:

1. place source PDFs in the expected source directory
2. run `python3 scripts/build_exam_data.py`
3. review suspicious output with text/unified review tooling
4. run `python3 scripts/build_release_data.py`
5. verify `release-data/`
6. run application smoke checks against the refreshed dataset

## Testing notes

The test suite covers both self-contained and integration-style pipeline behavior.

- fixture-based tests create temporary datasets
- repository-level tests may assume external data exists
- release-data validation tests can run against the committed runtime dataset
