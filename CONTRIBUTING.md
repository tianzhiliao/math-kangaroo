# Contributing

This repository is maintained as a small collaborative engineering project. The goal of this guide is to keep changes understandable, testable, and documented.

## Before you start

1. Read [README.md](README.md).
2. Read [docs/development.md](docs/development.md).
3. Make sure you understand whether your change touches:
   - frontend/runtime behavior
   - FastAPI AI behavior
   - release-data schema or content pipeline behavior

## Setup

- install web dependencies in `apps/web`
- install API dependencies from `apps/api/requirements.txt`
- create `.env` from `.env.example`
- use `./scripts/dev.sh` for the default local stack

## Branches and commits

- keep branches focused on one coherent change
- prefer small, reviewable commits
- write commit messages that describe the behavior change, not just the file list

## Validation expectations

For most frontend or route-handler changes:

```bash
cd apps/web
npm run lint
npm run build
```

For API or pipeline changes:

```bash
python3 -m unittest discover -s tests -v
```

If a known external-data dependency prevents a pipeline test from running in your environment, call that out clearly in your change summary.

## Documentation rules

If you change any of the following, update documentation in the same change:

- public behavior
- startup flow
- environment variables
- API request or response shapes
- `release-data` schema or path semantics
- deployment expectations

At minimum, review whether these files need updates:

- `README.md`
- `docs/development.md`
- `docs/api.md`
- `docs/release-data-format.md`
- `docs/deployment.md`
- `docs/troubleshooting.md`

## Working with data and generated artifacts

- do not assume `original_pdf_data/` exists in every checkout
- treat `release-data/` as the runtime contract
- be careful when changing pipeline outputs that feed the web app and FastAPI

If you modify extraction or release generation logic, review:

- `src/kangaroo_pdf`
- `scripts/`
- `tests/`
- affected docs

## Pull request checklist

- code or docs match the actual repository behavior
- validation steps were run, or skipped with a clear reason
- docs were updated when interfaces changed
- no secrets were committed
- `.env` was not added to version control
