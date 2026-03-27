# Deployment

This guide covers the current deployment shapes for private or beta environments.

## Recommended first public beta: Vercel frontend only

If you want to share the app quickly without deploying FastAPI yet, deploy only `apps/web` to Vercel.

This works because the Next.js app reads the checked-in `release-data/` dataset directly for:

- `/api/exams`
- `/api/exams/[examId]`
- `/api/exams/[examId]/raw/[...path]`
- `/api/practice-bank`

### Vercel project settings

- import the GitHub repository
- set Root Directory to `apps/web`
- keep the default Next.js framework detection
- use Node.js `20`
- start with the generated production `.vercel.app` domain

### Required Vercel environment variables

- `NEXT_PUBLIC_ENABLE_AI=false`
- `ENABLE_AI=false`

### Behavior in this mode

- exam and practice flows stay available
- AI explanation and TTS UI are hidden
- `/api/ai/explanation` returns `404` with `feature_disabled`
- `/api/ai/tts` returns `404` with `feature_disabled`

### Why the extra Next.js config exists

The web app lives in `apps/web`, but its runtime data lives in the repo-level `release-data/` directory.
The Next.js config uses `outputFileTracingRoot` and `outputFileTracingIncludes` so Vercel includes those files in the deployed server bundle.

## Current deployment model

The repository is deployed as two application processes:

- Next.js web server
- FastAPI backend

Both services read from the same runtime dataset:

- `release-data/`

The web server also proxies AI requests to FastAPI through `FASTAPI_BASE_URL`.

## Docker images

### Web

Defined in `docker/Dockerfile.web`.

Behavior:

- installs `apps/web` dependencies
- copies the web app into the image
- copies `release-data/` into `/data/release-data`
- sets `RELEASE_DATA_PATH=/data/release-data`
- builds the Next.js application
- starts the app with `npm start`

### API

Defined in `docker/Dockerfile.api`.

Behavior:

- installs `apps/api/requirements.txt`
- copies the API app into the image
- copies `release-data/` into `/data/release-data`
- sets `RELEASE_DATA_PATH=/data/release-data`
- serves the app with Uvicorn on port `8000`

## Docker Compose

For local full-stack containers:

```bash
docker compose up --build
```

The compose file wires:

- `web` on port `3000`
- `api` on port `8000`
- `FASTAPI_BASE_URL=http://api:8000` inside the web container
- `RELEASE_DATA_PATH=/data/release-data` for both services

## Required environment variables

### Required

- none for the frontend-only Vercel mode

### Required for full-stack AI deployments

- `OPENAI_API_KEY`

### Runtime configuration

- `NEXT_PUBLIC_ENABLE_AI`
- `ENABLE_AI`
- `FASTAPI_BASE_URL`
- `RELEASE_DATA_PATH`
- `API_CACHE_DIR`
- `OPENAI_TTS_MODEL`
- `OPENAI_TTS_VOICE`
- `OPENAI_EXPLANATION_MODEL`
- `TTS_CACHE_TTL_SECONDS`
- `TTS_CACHE_MAX_ITEMS`

## Deployment checklist

Before promoting a build:

1. Ensure `release-data/` is present and matches the version you intend to ship.
2. Run `cd apps/web && npm run build`.
3. If you are shipping AI features, run `python3 -m unittest discover -s tests -v` and confirm any failures are understood.
4. For frontend-only Vercel, verify `NEXT_PUBLIC_ENABLE_AI=false` and `ENABLE_AI=false`.
5. For full-stack deployments, verify `OPENAI_API_KEY` is configured in the target environment.
6. For full-stack deployments, confirm the web service can reach FastAPI through `FASTAPI_BASE_URL`.
7. For full-stack deployments, confirm the API service can write to its cache directory.

## Health and smoke checks

### Existing health check

FastAPI exposes:

- `GET /health`

Expected response:

```json
{ "ok": true }
```

### Suggested web smoke checks

The web app does not currently expose a dedicated health endpoint. For beta deployments, use one or more of:

- `GET /`
- `GET /api/exams`
- `GET /api/practice-bank`

## Beta deployment constraints

The current stack is suitable for private or small beta environments, but it is not hardened for unrestricted public traffic.

Current gaps to account for operationally:

- no built-in user authentication
- no built-in rate limiting
- no formal secret rotation workflow in the repo
- limited observability and error reporting

Recommended beta posture:

- deploy behind private ingress or allowlisted access where possible
- store `OPENAI_API_KEY` in the platform secret manager, never in the image
- keep `API_CACHE_DIR` on writable storage with enough space for TTS/audio cache growth
- monitor FastAPI errors, especially AI upstream failures and malformed requests

## Release-data concerns

`release-data/` is a deployable runtime artifact. If you refresh it:

- rebuild the web image
- rebuild the API image
- run a basic smoke test against manifest and exam endpoints
- verify that referenced assets exist under `release-data/exams/<exam_id>/assets/`

## Rollback guidance

If a deployment fails after a data refresh:

1. roll back both the application image and the `release-data` version together
2. verify `/health` on FastAPI
3. verify `/api/exams` on Next.js
4. verify one AI explanation request and one TTS request after rollback
