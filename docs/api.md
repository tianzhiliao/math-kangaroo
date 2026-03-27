# API Reference

This repository has two HTTP layers:

1. Next.js route handlers in `apps/web/app/api`
2. FastAPI upstream endpoints in `apps/api/app/routers`

The browser usually talks to the Next.js layer. The Next.js layer either reads `release-data/` directly or proxies requests to FastAPI.

## Next.js route handlers

## `GET /api/exams`

Reads:

- `release-data/manifest.json`

Success response:

- `200 application/json`
- returns the parsed manifest payload

Failure response:

- `500 application/json`
- `{ "error": "manifest_not_found", "message": "Could not read release-data/manifest.json" }`

## `GET /api/exams/[examId]`

Reads:

- `release-data/exams/<examId>/exam.json`

Success response:

- `200 application/json`
- returns the parsed exam payload

Failure response:

- `404 application/json`
- `{ "error": "exam_not_found" }`

## `GET /api/exams/[examId]/raw/[...path]`

Serves raw files from the selected exam directory under `release-data/exams/<examId>/`.

Supported content types currently inferred by file suffix:

- `.png` -> `image/png`
- `.json` -> `application/json`
- anything else -> `application/octet-stream`

Special behavior:

- rejects path traversal attempts with `403`
- returns immutable cache headers on success

Failure responses:

- `404 text/plain` when the path is missing
- `403 text/plain` when the resolved path escapes the exam directory

## `GET /api/practice-bank`

Builds a flattened practice bank from all exams listed in `release-data/manifest.json`.

Success response:

- `200 application/json`

Shape:

```json
{
  "total": 123,
  "entries": [
    {
      "exam_id": "canada-gr0102e-2023",
      "question_number": 1,
      "correct_label": "B"
    }
  ]
}
```

Failure response:

- `500 application/json`
- `{ "error": "practice_bank_failed" }`

## `POST /api/ai/explanation`

Purpose:

- proxies an explanation request to FastAPI `/ai/explanation`

Request body:

```json
{
  "exam_id": "canada-gr0102e-2023",
  "question_number": 1,
  "selected_label": "A",
  "force_refresh": false
}
```

Success response:

- `200 application/json`

Shape:

```json
{
  "exam_id": "canada-gr0102e-2023",
  "question_number": 1,
  "selected_label": "A",
  "correct_label": "B",
  "explanation": "Count slowly. So the answer is B.",
  "model": "gpt-5.4",
  "cache_hit": false,
  "generated_at": "2026-03-26T00:00:00Z"
}
```

Common failure cases:

- backend unreachable -> `502`
- upstream validation failure -> proxied status code
- malformed upstream JSON -> `502`

## `GET /api/ai/tts`

Purpose:

- proxies a streaming TTS request to FastAPI `GET /tts`

Query parameters:

- `exam_id`
- `question_number`
- `voice` optional
- `speed` optional
- `format` optional

Success response:

- `200`
- `audio/*` streaming body

## `POST /api/ai/tts`

Purpose:

- proxies a JSON TTS request to FastAPI `POST /tts`

Request body:

```json
{
  "exam_id": "canada-gr0102e-2023",
  "question_number": 1,
  "voice": "alloy",
  "speed": 1.0,
  "format": "opus"
}
```

Success response:

- `200`
- `audio/*` streaming body

## FastAPI upstream endpoints

## `GET /health`

Purpose:

- basic readiness/liveness check

Success response:

```json
{ "ok": true }
```

## `GET /manifest`

Purpose:

- load the runtime manifest directly from `release-data`

## `GET /exams/{exam_id}`

Purpose:

- load the runtime exam JSON directly from `release-data`

Failure response:

- `404` if the exam does not exist

## `POST /ai/explanation`

Purpose:

- generate a short child-friendly explanation for a multiple-choice question

Request body fields:

- `exam_id` string
- `question_number` integer >= 1
- `selected_label` optional string
- `force_refresh` boolean, default `false`

Response fields:

- `exam_id`
- `question_number`
- `selected_label`
- `correct_label`
- `explanation`
- `model`
- `cache_hit`
- `generated_at`

Notes:

- explanations are cached on disk by request payload
- invalid `selected_label` values return `422`
- missing OpenAI configuration returns `500`

## `GET /tts`

Query parameters:

- `exam_id`
- `question_number`
- `voice` optional
- `speed` between `0.25` and `4.0`
- `format` in `mp3`, `opus`, `aac`, `flac`, `wav`, or `pcm`

Response:

- streaming audio body

## `POST /tts`

JSON body fields:

- `exam_id`
- `question_number`
- `voice` optional
- `speed`
- `format`

Response:

- streaming audio body

Common failure cases:

- `422` when `question_number` or `speed` is invalid
- `422` when there is no stem text for the selected question
- `500` when OpenAI configuration is unavailable

## Environment dependencies

Important runtime configuration used by the API layers:

- `FASTAPI_BASE_URL`
- `RELEASE_DATA_PATH`
- `OPENAI_API_KEY`
- `API_CACHE_DIR`
- `OPENAI_TTS_MODEL`
- `OPENAI_TTS_VOICE`
- `OPENAI_EXPLANATION_MODEL`

## Which layer should you debug?

- If browser UI loads exams but AI features fail, inspect the FastAPI layer and proxy configuration.
- If `/api/exams` fails, inspect `release-data/` and Next.js route handlers.
- If FastAPI content routes fail, inspect `RELEASE_DATA_PATH` and the on-disk dataset.
