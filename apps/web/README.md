# Web App

This directory contains the Next.js frontend for the Math Web App repository.

For project-wide setup, startup, deployment, and architecture, start with the root documentation:

- [`../../README.md`](../../README.md)
- [`../../docs/development.md`](../../docs/development.md)
- [`../../docs/api.md`](../../docs/api.md)

## What lives here

- App Router pages under `app/`
- Next.js route handlers under `app/api/`
- frontend components under `components/`
- shared frontend utilities under `lib/`

## Local web development

Install dependencies:

```bash
cd apps/web
npm install
```

Run the web app only:

```bash
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

- <http://127.0.0.1:3000>

If you run only the web app with `NEXT_PUBLIC_ENABLE_AI=false` and `ENABLE_AI=false`, exam and practice mode still work without FastAPI.

## Recommended full-stack startup

From the repository root:

```bash
./scripts/dev.sh
```

That starts both:

- Next.js on port `3000`
- FastAPI on port `8000`

## Build and run

Production build:

```bash
npm run build
```

Production server:

```bash
npm start
```

## Web-specific environment variables

| Variable            | Description                                      |
| ------------------- | ------------------------------------------------ |
| `NEXT_PUBLIC_ENABLE_AI` | Enables AI UI in the browser when set to `true`. |
| `ENABLE_AI` | Enables Next.js AI proxy routes when set to `true`. |
| `RELEASE_DATA_PATH` | Absolute path to `release-data` (Docker / prod). |
| `FASTAPI_BASE_URL`  | Base URL for the FastAPI backend proxy when AI is enabled. |

## Vercel frontend-only deployment

For the first shareable beta, deploy this app to Vercel without the FastAPI service:

- import the repository into Vercel
- set Root Directory to `apps/web`
- set `NEXT_PUBLIC_ENABLE_AI=false`
- set `ENABLE_AI=false`

This keeps the release-data-backed routes available and hides AI explanation/TTS UI.

## API surface implemented in this app

These route handlers are implemented in `apps/web/app/api`:

- `/api/exams`
- `/api/exams/[examId]`
- `/api/exams/[examId]/raw/[...path]`
- `/api/practice-bank`
- `/api/ai/explanation`
- `/api/ai/tts`

See [`../../docs/api.md`](../../docs/api.md) for endpoint details.
