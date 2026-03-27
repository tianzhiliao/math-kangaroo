# Deployment

This guide covers the current deployment shape for private or beta environments.

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

- `OPENAI_API_KEY`

### Runtime configuration

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
3. Run `python3 -m unittest discover -s tests -v` and confirm any failures are understood.
4. Verify `OPENAI_API_KEY` is configured in the target environment.
5. Confirm the web service can reach FastAPI through `FASTAPI_BASE_URL`.
6. Confirm the API service can write to its cache directory.

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
