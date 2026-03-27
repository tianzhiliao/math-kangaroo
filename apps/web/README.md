# Web app (Next.js)

## Run locally

From repo root:

```bash
./scripts/dev.sh
```

This starts both the Next.js web app and the FastAPI backend used by TTS and explanations.

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

The app reads `release-data/` via API routes (`../../release-data` from `apps/web`).

## Manual startup

If you only run the web app, the AI buttons will fail because the FastAPI backend will be missing.

Web only:

```bash
cd apps/web
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

API only:

```bash
set -a
source .env
set +a
python3 -m uvicorn main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

## Docker Compose

Full-stack Docker development is also available:

```bash
docker compose up --build
```

## Production

```bash
npm run build
npm start
```

## Environment

| Variable            | Description                                      |
| ------------------- | ------------------------------------------------ |
| `RELEASE_DATA_PATH` | Absolute path to `release-data` (Docker / prod). |
| `FASTAPI_BASE_URL`  | Base URL for the FastAPI backend proxy.          |
