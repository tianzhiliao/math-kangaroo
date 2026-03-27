# Troubleshooting

This page covers common issues seen in local development and beta-style deployments.

## `.env` is missing

Symptom:

- `./scripts/dev.sh` exits immediately with a message about a missing `.env`

Cause:

- the dev script requires a repository-root `.env`

Fix:

```bash
cp .env.example .env
```

Then fill in at least `OPENAI_API_KEY`.

## `OPENAI_API_KEY` is missing

Symptoms:

- `./scripts/dev.sh` refuses to start
- FastAPI explanation or TTS requests return configuration errors

Cause:

- AI routes require a valid OpenAI API key

Fix:

- add `OPENAI_API_KEY` to `.env`
- restart the API service

## The website loads, but AI buttons fail

Symptoms:

- exam/practice pages load
- explanation or TTS requests fail
- proxy routes return a backend-unreachable message

Likely causes:

- FastAPI is not running
- `FASTAPI_BASE_URL` is wrong
- `OPENAI_API_KEY` is missing

Checks:

```bash
curl -sS http://127.0.0.1:8000/health
```

Expected:

```json
{ "ok": true }
```

If that fails, start the API or rerun:

```bash
./scripts/dev.sh
```

## `release-data` cannot be read

Symptoms:

- `/api/exams` returns `manifest_not_found`
- `/api/exams/[examId]` returns missing-data errors
- FastAPI content routes cannot find exams

Likely causes:

- `release-data/` is missing
- `RELEASE_DATA_PATH` points to the wrong location

Checks:

- confirm `release-data/manifest.json` exists
- confirm `RELEASE_DATA_PATH` is either unset or points to the intended directory

## `python3 -m unittest discover -s tests -v` fails on a clean clone

This can happen even when the web app still runs correctly.

Why:

- some tests are fixture-based and self-contained
- some tests expect source datasets, review artifacts, or generated inputs that are not committed to the repo

Common examples:

- missing `original_pdf_data/`
- missing generated review data
- repo-level dataset scope mismatches in pipeline tests

What to do:

- separate application-runtime failures from content-pipeline failures
- check whether the failing test is expecting upstream data outside the checked-in runtime dataset

## `pytest` is not found

Symptom:

- `pytest` is not installed or the command is missing

Explanation:

- the current repository standard is `unittest`, not `pytest`

Use:

```bash
python3 -m unittest discover -s tests -v
```

## FastAPI starts, but TTS returns errors

Possible causes:

- invalid `question_number`
- selected question has no stem text
- OpenAI service/configuration issue

Checks:

- verify the exam/question exists in `release-data`
- verify the selected question has `stem_text`
- verify `OPENAI_API_KEY`

## The web build passes, but runtime behavior still looks wrong

Remember:

- `npm run build` only validates the web app build
- the running application still depends on `release-data` and FastAPI

If the build passes but runtime fails:

1. check `/api/exams`
2. check FastAPI `/health`
3. check environment variables
4. verify the selected dataset matches what you intended to ship

## Docker deployment works locally but not in another environment

Checks:

- confirm `OPENAI_API_KEY` is provided to the API container
- confirm the web container can resolve the API hostname
- confirm `RELEASE_DATA_PATH` matches the mounted or copied data directory
- confirm the API cache directory is writable

## When to inspect which layer

- UI navigation issue -> `apps/web/app` and `apps/web/components`
- data loading issue -> Next.js route handlers and `release-data`
- AI explanation or TTS issue -> `apps/api/app/services` and FastAPI config
- content-structure issue -> `src/kangaroo_pdf` and pipeline scripts
