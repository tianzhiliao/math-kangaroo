# Math Web App

Math Web App is a small full-stack repository for Math Kangaroo prep content. It combines:

- a Next.js web client in `apps/web`
- a FastAPI service in `apps/api`
- a Python PDF/data pipeline in `src/kangaroo_pdf`
- a checked-in `release-data/` dataset consumed by the web and API layers

The repository is designed for developer collaborators. The goal of this documentation set is to help a new engineer understand the stack, run it locally, and know where to look for data, AI, and pipeline behavior within a few minutes.

## Current capabilities

- Exam mode with timed question flow
- Practice mode with per-question feedback
- Optional AI-generated explanations via FastAPI + OpenAI
- Optional text-to-speech generation for question stems
- `release-data` manifest/exam loading through Next.js route handlers
- PDF extraction, review, and release-data build tooling for content preparation

## Repository map

```text
.
|-- apps/
|   |-- api/              FastAPI backend for AI explanation and TTS
|   `-- web/              Next.js frontend and server route handlers
|-- docs/                 Project-level technical documentation
|-- release-data/         Frontend/API-ready dataset checked into the repo
|-- scripts/              Operational scripts for local dev and data workflows
|-- src/kangaroo_pdf/     PDF extraction, review, and release build pipeline
`-- tests/                Python test suite for API and data pipeline code
```

## Quick start

### Prerequisites

- Node.js 20+
- npm 10+
- Python 3.12+
- `curl`, `lsof`, and a working shell environment

### 1. Install dependencies

Web dependencies:

```bash
cd apps/web
npm install
cd ../..
```

API dependencies:

```bash
python3 -m pip install -r apps/api/requirements.txt
```

If you plan to work on the PDF/data pipeline, your Python environment also needs the third-party packages imported by `src/kangaroo_pdf`, such as `Pillow`, `PyMuPDF`, `pypdf`, `pdfplumber`, and `python-dotenv`.

### 2. Create `.env`

Copy the example file:

```bash
cp .env.example .env
```

For frontend-only usage, keep these flags set to `false`:

- `NEXT_PUBLIC_ENABLE_AI`
- `ENABLE_AI`

Only set `OPENAI_API_KEY` and point `FASTAPI_BASE_URL` at a running FastAPI service when you want AI explanation and TTS enabled.

### 3. Start local development

From the repository root:

```bash
./scripts/dev.sh
```

This starts:

- Next.js at `http://127.0.0.1:3000`
- FastAPI at `http://127.0.0.1:8000`

The script expects a root `.env` file. If you enable AI in that file, it also expects a valid `OPENAI_API_KEY`.

## Alternative startup paths

### Web only

```bash
cd apps/web
npm run dev -- --hostname 127.0.0.1 --port 3000
```

### API only

```bash
set -a
source .env
set +a
python3 -m uvicorn main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

### Docker Compose

```bash
docker compose up --build
```

## Verification

### Web

Production build:

```bash
cd apps/web
npm run build
```

### Python

Current recommended test entrypoint:

```bash
python3 -m unittest discover -s tests -v
```

Notes:

- `pytest` is not the repository's current standard entrypoint.
- Some pipeline tests expect external source datasets or generated review inputs that are not checked into this repository.
- `release-data/` is committed, but `original_pdf_data/` is intentionally not part of the repo by default.

## Key runtime interfaces

### Environment variables

- `NEXT_PUBLIC_ENABLE_AI`
- `ENABLE_AI`
- `OPENAI_API_KEY`
- `FASTAPI_BASE_URL`
- `RELEASE_DATA_PATH`
- `API_CACHE_DIR`
- `OPENAI_TTS_MODEL`
- `OPENAI_TTS_VOICE`
- `OPENAI_EXPLANATION_MODEL`
- `TTS_CACHE_TTL_SECONDS`
- `TTS_CACHE_MAX_ITEMS`

### Main routes

Next.js route handlers:

- `/api/exams`
- `/api/exams/[examId]`
- `/api/exams/[examId]/raw/[...path]`
- `/api/practice-bank`
- `/api/ai/explanation`
- `/api/ai/tts`

FastAPI upstream endpoints:

- `/health`
- `/manifest`
- `/exams/{exam_id}`
- `/ai/explanation`
- `/tts`

## Documentation map

- [Architecture](docs/architecture.md)
- [Development](docs/development.md)
- [Deployment](docs/deployment.md)
- [Data pipeline](docs/data-pipeline.md)
- [Release-data format](docs/release-data-format.md)
- [API reference](docs/api.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](CONTRIBUTING.md)
- [Web app README](apps/web/README.md)

## Vercel frontend-only deployment

For the first public beta, you can deploy only `apps/web` to Vercel and leave `apps/api` offline.

Use this setup:

- import the GitHub repository into Vercel
- set the project Root Directory to `apps/web`
- set `NEXT_PUBLIC_ENABLE_AI=false`
- set `ENABLE_AI=false`

This keeps exam and practice features online while hiding AI explanation and TTS UI.

## Known project boundaries

- The repository is optimized for developer collaboration and private/beta use.
- Authentication, rate limiting, and public-production hardening are not fully built into the current stack.
- The committed `release-data/` dataset is the runtime input for the web app, while the full PDF source corpus and some review artifacts live outside the repository by design.
