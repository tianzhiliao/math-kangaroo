# Kangaroo Math

Kangaroo Math is a small full-stack app for practicing Kangaroo Math questions, taking timed exam papers, and playing stem audio generated through OpenAI TTS.

The repository has two runtime pieces:

- `frontend/`: a React + TypeScript + Vite app for practice mode, timed exam mode, and result review
- `backend/`: a FastAPI app that serves stem audio at `/api/tts/...` and can also serve the built frontend

## Repository Layout

- `backend/` FastAPI app, TTS client, cache service, and backend tests
- `frontend/` Vite app, static exam assets under `public/data/`, and frontend unit tests
- `docs/` runtime schema notes for the committed exam data

## Prerequisites

- Python 3.10+
- Node.js LTS
- npm

## Quick Start

### 1. Set up the backend

Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`OPENAI_API_KEY` is required if you want working stem audio. Without it, the backend still starts, but `/api/health` reports a misconfigured state and the frontend will show audio as unavailable.

### 2. Set up the frontend

```bash
cd frontend
npm install
cp .env.example .env
```

The frontend proxies `/api` requests to `VITE_API_PROXY_TARGET`, which defaults to `http://127.0.0.1:8000`.

### 3. Start both services

Start the FastAPI backend from the repository root:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal, start the frontend dev server:

```bash
cd frontend
npm run dev
```

Then open the local Vite URL shown in the terminal, usually `http://127.0.0.1:3000/`.

## Minimal Integration Check

With the backend running, confirm the API is reachable:

```bash
curl -sS http://127.0.0.1:8000/api/health
```

Expected result:

- with `OPENAI_API_KEY` configured: `{"status":"ok"}`
- without `OPENAI_API_KEY`: a `500` response describing the missing key

To confirm the frontend proxy is pointed at the backend, visit the app and try the stem-audio control on a question card. The frontend checks `/api/health` before enabling audio playback.

## Build, Test, and Lint

### Frontend

Run from `frontend/`:

```bash
npm test
npm run lint
npm run build
```

### Backend

Run from the repository root:

```bash
python -m unittest discover backend/tests
```

## Serving the Built Frontend from FastAPI

The backend automatically serves the built frontend when `frontend/dist/` exists.

Build the frontend:

```bash
cd frontend
npm run build
```

Then start the backend from the repository root:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` to load the bundled app through FastAPI.

## Environment Files

### Backend `.env`

See `/.env.example` for all supported settings:

- `OPENAI_API_KEY` required for TTS
- `TTS_MODEL`, `TTS_VOICE`, `TTS_RESPONSE_FORMAT`, `TTS_TIMEOUT_SECONDS` optional OpenAI TTS overrides
- `EXAM_DATA_DIR` overrides where the backend reads exam JSON files
- `TTS_CACHE_DIR` overrides the audio cache location
- `FRONTEND_DIST_DIR` overrides the directory served by FastAPI for built frontend assets

Important: relative paths are easiest to use when you start `uvicorn` from the repository root. If you launch the backend from another directory, prefer absolute paths in `.env`.

### Frontend `.env`

See `frontend/.env.example`:

- `VITE_API_PROXY_TARGET` sets the local backend origin used by the Vite dev proxy

## Runtime Data Assets

The app reads committed exam JSON and SVG assets from `frontend/public/data/`. By default, the backend uses that same directory as `EXAM_DATA_DIR`, so both sides read the same question set during local development.

Runtime data reference:

- [docs/canonical-exam-schema.md](docs/canonical-exam-schema.md)

## API Summary

- `GET /api/health` reports whether the backend is ready to serve TTS
- `GET /api/tts/exams/{exam_id}/questions/{question_id}/stem.wav` returns cached or streamed WAV audio for a question stem

## Optional Cache Warm-Up

If you already have `OPENAI_API_KEY` configured and want to pre-generate stem audio files into `.cache/tts/`, run:

```bash
python -m backend.scripts.prewarm_stem_tts
```
