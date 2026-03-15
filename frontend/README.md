# Kangaroo Math Frontend

This package contains the React + TypeScript + Vite frontend for Kangaroo Math.

The UI supports:

- a home screen that routes into practice mode or timed exam mode
- full-paper exam sessions for the bundled `Exam_2020` to `Exam_2023` datasets
- practice sessions that combine questions across exam papers
- result review screens and optional stem-audio playback when the backend is available

For full-stack setup, backend instructions, and data-pipeline notes, see the repository root [README](../README.md).

## Local Development

```bash
cp .env.example .env
npm install
npm run dev
```

By default, the Vite dev server proxies `/api` requests to `http://127.0.0.1:8001`. Override that in `.env` with:

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8001
```

## Available Scripts

- `npm run dev` start the Vite dev server
- `npm run build` type-check and build the production bundle
- `npm run lint` run ESLint
- `npm test` run Vitest unit tests
- `npm run preview` serve the production build locally

## Data Expectations

- runtime exam JSON lives under `public/data/*.json`
- SVG assets live under `public/data/svg/`
- the frontend fetches exam papers directly from `/data/<exam_id>.json`
- during local development, the backend usually reads the same data directory by default

## Backend Dependency

The frontend can run without a working OpenAI key, but question-audio controls stay unavailable until `/api/health` reports that the backend is actually ready to serve TTS.

The frontend uses `/api/health` as the gate for showing question-audio controls. When playback itself fails and the backend returns a JSON error response, the UI can surface that backend-provided detail instead of only showing a generic unavailable message.

For backend startup, readiness states, and TTS troubleshooting notes, use the repository root [README](../README.md).
