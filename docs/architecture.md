# Architecture

This repository has three main layers:

1. Next.js web application
2. FastAPI AI backend
3. Python PDF/data pipeline

## System overview

```text
original_pdf_data/ and working data
        |
        v
src/kangaroo_pdf + scripts/
        |
        v
release-data/
        |
        +--> apps/web route handlers
        |
        +--> apps/api content loaders
```

## 1. Web layer

Location: `apps/web`

Responsibilities:

- render the exam and practice UI
- load manifest/exam data from `release-data/`
- proxy AI requests to FastAPI
- serve raw release assets such as PNGs through Next.js route handlers

Important implementation areas:

- `app/` for pages and route handlers
- `components/` for exam/practice/question UI
- `lib/paths.ts` for resolving `release-data`
- `lib/fastapi.ts` and `lib/fastapi-proxy.ts` for upstream API access

## 2. FastAPI layer

Location: `apps/api`

Responsibilities:

- expose AI explanation and TTS endpoints
- read `release-data` for manifest/exam/question lookups
- manage API-side caches for explanation JSON and TTS audio
- provide a simple health endpoint

Important implementation areas:

- `app/main.py` for app wiring
- `app/routers/` for HTTP endpoints
- `app/services/explanations.py` for AI explanation generation
- `app/services/tts.py` for streaming TTS responses
- `app/question_loader.py` for release-data lookups

## 3. PDF/data pipeline

Location: `src/kangaroo_pdf` and `scripts/`

Responsibilities:

- classify source PDFs
- extract exam content and answer tables
- produce intermediate review data
- support manual/unified review tooling
- generate and validate the final `release-data/` package consumed by runtime services

Important implementation areas:

- `pipeline.py` for core extraction
- `text_review_pipeline.py` for review dataset generation
- `unified_review.py` for the local review tool
- `release_pipeline.py` for release-data build and validation

## Data flow in practice

### Source and working datasets

The full source PDF corpus is expected outside the checked-in runtime dataset. Typical working directories include:

- `original_pdf_data/` for raw PDFs
- `.generated/` or equivalent working data for extracted intermediate artifacts
- `review-data/` and `reports/` for inspection and review output

These directories are not all guaranteed to exist in a fresh clone.

### Runtime dataset

`release-data/` is the stable runtime dataset:

- `release-data/manifest.json` lists available exams
- `release-data/exams/<exam_id>/exam.json` stores question and asset metadata
- `release-data/exams/<exam_id>/assets/...` stores image assets referenced by questions

The web app and API both treat `release-data/` as the primary content interface.

## Why `release-data/` is in the repo but `original_pdf_data/` is not

This is intentional.

- `release-data/` is lightweight enough to ship with the application and is needed for local runtime behavior.
- `original_pdf_data/` is an upstream content source, not the deployment artifact.
- Some pipeline and review tests assume those upstream inputs exist, which is why a clean clone can still have data-workflow tests that fail unless the external source dataset is available.

## Architectural constraints

- The Next.js app depends on FastAPI for AI explanation and TTS.
- The FastAPI app depends on `release-data/` and OpenAI credentials.
- The pipeline can be worked on independently from the web app, but its outputs eventually feed both runtime layers.
- There is no single root Python packaging file today; Python tooling spans API code, pipeline code, and test code.
