# Kangaroo Math

Kangaroo Math is a small full-stack app for practicing Kangaroo Math questions, taking timed exam papers, and playing stem audio generated through OpenAI TTS.

The repository has two runtime pieces:

- `frontend/`: a React + TypeScript + Vite app for practice mode, timed exam mode, and result review
- `backend/`: a FastAPI app that serves stem audio at `/api/tts/...` and can also serve the built frontend

## Repository Layout

- `backend/` FastAPI app, TTS client, cache service, and backend tests
- `frontend/` Vite app, static exam assets under `public/data/`, and frontend unit tests
- `docs/` runtime schema notes for the committed exam data
- `Dockerfile` multi-stage image build for public deployment

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

`OPENAI_API_KEY` is required if you want working stem audio. Without it, the backend still starts, but `/api/health` reports a misconfigured state and the frontend will keep audio controls unavailable.

### 2. Set up the frontend

```bash
cd frontend
npm install
cp .env.example .env
```

The frontend proxies `/api` requests to `VITE_API_PROXY_TARGET`, which defaults to `http://127.0.0.1:8001`.

### 3. Start both services

Start the FastAPI backend from the repository root:

```bash
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
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
curl -sS http://127.0.0.1:8001/api/health
```

Expected result:

- with `OPENAI_API_KEY` configured and a backend that can reach OpenAI: `{"status":"ok"}`
- with `OPENAI_API_KEY` configured but no outbound OpenAI access: a `503` response describing the connectivity problem
- without `OPENAI_API_KEY`: a `500` response describing the missing key

To confirm the frontend proxy is pointed at the backend, visit the app and try the stem-audio control on a question card. The frontend checks `/api/health` before enabling audio playback, and will surface backend-provided failure details when playback cannot be completed.

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
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/` to load the bundled app through FastAPI.

## Docker Local Verification

Build the production image from the repository root:

```bash
docker build -t kangaroo-math .
```

Run the container locally:

```bash
docker run --rm -p 8001:8001 kangaroo-math
```

Then verify the public-serving behavior:

```bash
curl -sS http://127.0.0.1:8001/
curl -sS http://127.0.0.1:8001/api/livez
curl -i http://127.0.0.1:8001/api/health
```

Expected result for a first public release without `OPENAI_API_KEY`:

- `/` serves the built app
- `/api/livez` returns `200 {"status":"ok"}`
- `/api/health` returns `500` because TTS is intentionally not configured yet
- practice mode and timed exam mode still work, while question audio remains unavailable

## Render Deployment

This repository is ready to deploy as a single public web service on Render using the root `Dockerfile`.

### Recommended first release

- deploy the `main` branch from `https://github.com/tianzhiliao/math-kangaroo`
- create a `Web Service`
- let Render build from the repository `Dockerfile`
- set the health check path to `/api/livez`
- do not set `OPENAI_API_KEY` for the first release

### Render setup steps

1. In Render, create a new `Web Service` from the GitHub repository.
2. Keep the root directory as the repository root so Render uses the root `Dockerfile`.
3. Leave build and start commands empty when using the Docker deployment flow.
4. Set `Health Check Path` to `/api/livez`.
5. Deploy the service and use the Render-generated URL as the first public address.

The container listens on `0.0.0.0` and reads the platform-provided `PORT`, so no extra port configuration is required.

### Expected production behavior without TTS

- the site is publicly reachable from the Render URL
- exam JSON and SVG assets are served by the built frontend bundle
- `/api/livez` reports the service is up
- `/api/health` reports TTS is misconfigured until `OPENAI_API_KEY` is added
- question-audio controls stay unavailable by design, which is expected for the first release

If you later want to enable TTS, add `OPENAI_API_KEY` in Render environment variables and redeploy.

## Environment Files

### Backend `.env`

See `/.env.example` for all supported settings:

- `OPENAI_API_KEY` required for TTS
- `TTS_MODEL`, `TTS_VOICE`, `TTS_TIMEOUT_SECONDS` optional OpenAI TTS overrides
- `TTS_RESPONSE_FORMAT` must stay `wav`; the audio API only serves WAV responses
- `EXAM_DATA_DIR` overrides where the backend reads exam JSON files
- `TTS_CACHE_DIR` overrides the audio cache location
- `FRONTEND_DIST_DIR` overrides the directory served by FastAPI for built frontend assets

For the first public deployment, you can leave `OPENAI_API_KEY` unset. The site still works, but `/api/health` reports that TTS is unavailable and the frontend keeps audio controls disabled.

Important: relative paths are easiest to use when you start `uvicorn` from the repository root. If you launch the backend from another directory, prefer absolute paths in `.env`.

### Frontend `.env`

See `frontend/.env.example`:

- `VITE_API_PROXY_TARGET` sets the local backend origin used by the Vite dev proxy; this repo's local default is `http://127.0.0.1:8001`

## Runtime Data Assets

The app reads committed exam JSON and SVG assets from `frontend/public/data/`. By default, the backend uses that same directory as `EXAM_DATA_DIR`, so both sides read the same question set during local development.

Runtime data reference:

- [docs/canonical-exam-schema.md](docs/canonical-exam-schema.md)

If you start the backend from a restricted sandbox or environment without outbound network access, `/api/health` will report the backend as unavailable and the frontend will keep audio controls disabled instead of showing a false ready state.

## API Summary

- `GET /api/livez` reports that the web service process is running and should be used for deployment health checks
- `GET /api/health` reports whether the backend is actually ready to serve TTS, including OpenAI reachability
- `GET /api/tts/exams/{exam_id}/questions/{question_id}/stem.wav` returns cached or streamed WAV audio for a question stem

## Optional Cache Warm-Up

If you already have `OPENAI_API_KEY` configured and want to pre-generate stem audio files into `.cache/tts/`, run:

```bash
python -m backend.scripts.prewarm_stem_tts
```
