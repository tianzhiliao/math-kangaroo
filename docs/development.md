# Development

This guide is the main local-development reference for contributors.

## Recommended toolchain

- Node.js 20+
- npm 10+
- Python 3.12+
- macOS or Linux shell with `curl` and `lsof`

The Dockerfiles also use Node 20 and Python 3.12, so matching those locally reduces surprises.

## Repository setup

### Web dependencies

```bash
cd apps/web
npm install
cd ../..
```

### API dependencies

```bash
python3 -m pip install -r apps/api/requirements.txt
```

### Pipeline dependencies

The repository does not currently define a single root Python lockfile for the PDF pipeline. If you work on `src/kangaroo_pdf` or pipeline tests, install the packages imported by that codebase in your Python environment, including:

- `Pillow`
- `PyMuPDF`
- `pypdf`
- `pdfplumber`
- `python-dotenv`

## Environment variables

Create `.env` from the example file:

```bash
cp .env.example .env
```

Important variables:

- `OPENAI_API_KEY`: required for AI explanation and TTS
- `FASTAPI_BASE_URL`: used by the Next.js proxy routes; defaults to `http://127.0.0.1:8000`
- `RELEASE_DATA_PATH`: optional override for runtime data location
- `API_CACHE_DIR`: optional override for FastAPI cache files
- `OPENAI_TTS_MODEL`
- `OPENAI_TTS_VOICE`
- `OPENAI_EXPLANATION_MODEL`
- `TTS_CACHE_TTL_SECONDS`
- `TTS_CACHE_MAX_ITEMS`

## Starting the stack

### Recommended path

From the repository root:

```bash
./scripts/dev.sh
```

This script:

- validates required commands
- loads `.env`
- checks that `OPENAI_API_KEY` is present
- sets default values for `FASTAPI_BASE_URL` and `RELEASE_DATA_PATH`
- starts FastAPI on port `8000`
- starts Next.js on port `3000`
- waits for both services to become ready

### Manual startup

Web only:

```bash
cd apps/web
npm run dev -- --hostname 127.0.0.1 --port 3000
```

API only:

```bash
set -a
source .env
set +a
python3 -m uvicorn main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

## Common commands

### Web

Typecheck:

```bash
cd apps/web
npm run lint
```

Production build:

```bash
cd apps/web
npm run build
```

### Python tests

Current standard test command:

```bash
python3 -m unittest discover -s tests -v
```

Important notes:

- This repo currently uses `unittest` as the main Python test entrypoint.
- `pytest` is not the standard command here.
- Some tests are self-contained and run against temporary fixtures.
- Some pipeline tests expect external source datasets or generated inputs that may not exist in a fresh clone.

## Data workflow commands

Build structured exam data from source PDFs:

```bash
python3 scripts/build_exam_data.py
```

Build and validate release-data:

```bash
python3 scripts/build_release_data.py
```

Run the unified review tool:

```bash
python3 scripts/run_unified_review.py
```

Other helpful scripts live in `scripts/` for text review, AB comparison, answer syncing, and anomaly scanning.

## Where to make changes

### Frontend feature work

Look in:

- `apps/web/app`
- `apps/web/components`
- `apps/web/lib`

### FastAPI behavior

Look in:

- `apps/api/app/routers`
- `apps/api/app/services`
- `apps/api/app/question_loader.py`

### Dataset or pipeline behavior

Look in:

- `src/kangaroo_pdf`
- `scripts`
- `tests`

## Local development expectations

- Treat `release-data/` as the runtime contract for the app.
- Treat `original_pdf_data/` and other working directories as optional local inputs for content-processing workflows.
- If AI features fail in the browser while page rendering still works, first check whether FastAPI is running and whether `OPENAI_API_KEY` is set.
