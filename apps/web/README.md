# Web app (Next.js)

## Run locally

From repo root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The app reads `release-data/` via API routes (`../../release-data` from `apps/web`).

## Production

```bash
npm run build
npm start
```

## Environment

| Variable            | Description                                      |
| ------------------- | ------------------------------------------------ |
| `RELEASE_DATA_PATH` | Absolute path to `release-data` (Docker / prod). |
