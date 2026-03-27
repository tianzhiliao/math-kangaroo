#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_URL="http://127.0.0.1:8000/health"
WEB_URL="http://127.0.0.1:3000/"
API_LOG="/tmp/math-web-app-api.log"
WEB_LOG="/tmp/math-web-app-web.log"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

port_listener_pid() {
  lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -n 1
}

check_port_available() {
  local port="$1"
  local url="$2"
  local name="$3"
  local pid
  pid="$(port_listener_pid "$port" || true)"
  if [[ -z "${pid:-}" ]]; then
    return
  fi

  for _ in $(seq 1 5); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is already running on port $port (PID $pid). Stop it before running ./scripts/dev.sh."
      exit 1
    fi
    sleep 0.2
  done

  if curl -fsS "$url" >/dev/null 2>&1; then
    echo "$name is already running on port $port (PID $pid). Stop it before running ./scripts/dev.sh."
  else
    echo "Port $port is occupied by a nonresponsive process (PID $pid). Stop it before running ./scripts/dev.sh."
  fi
  exit 1
}

wait_for_service() {
  local url="$1"
  local name="$2"
  local log_path="$3"
  local pid="$4"

  for _ in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is ready."
      return 0
    fi
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "$name exited during startup. Last log lines:"
      tail -n 40 "$log_path" || true
      exit 1
    fi
    sleep 0.5
  done

  echo "$name did not become ready in time. Last log lines:"
  tail -n 40 "$log_path" || true
  exit 1
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "${WEB_PID:-}" ]] && kill -0 "$WEB_PID" >/dev/null 2>&1; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi

  wait "${WEB_PID:-}" >/dev/null 2>&1 || true
  wait "${API_PID:-}" >/dev/null 2>&1 || true
  exit "$exit_code"
}

require_command curl
require_command lsof
require_command npm
require_command python3

if [[ ! -f .env ]]; then
  echo "Missing .env at repo root."
  exit 1
fi

set -a
source .env
set +a

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is missing. Add it to .env before starting local dev."
  exit 1
fi

export FASTAPI_BASE_URL="${FASTAPI_BASE_URL:-http://127.0.0.1:8000}"
export RELEASE_DATA_PATH="${RELEASE_DATA_PATH:-$ROOT_DIR/release-data}"

check_port_available 8000 "$API_URL" "FastAPI"
check_port_available 3000 "$WEB_URL" "Next.js"

trap cleanup EXIT INT TERM

echo "Starting FastAPI on http://127.0.0.1:8000"
(cd "$ROOT_DIR/apps/api" && python3 -m uvicorn main:app --host 127.0.0.1 --port 8000) >"$API_LOG" 2>&1 &
API_PID=$!

echo "Starting Next.js on http://127.0.0.1:3000"
(cd "$ROOT_DIR/apps/web" && FASTAPI_BASE_URL="$FASTAPI_BASE_URL" npm run dev -- --hostname 127.0.0.1 --port 3000) >"$WEB_LOG" 2>&1 &
WEB_PID=$!

wait_for_service "$API_URL" "FastAPI" "$API_LOG" "$API_PID"
wait_for_service "$WEB_URL" "Next.js" "$WEB_LOG" "$WEB_PID"

echo
echo "Local dev is ready:"
echo "  Web: http://127.0.0.1:3000"
echo "  API: http://127.0.0.1:8000"
echo "Logs:"
echo "  $API_LOG"
echo "  $WEB_LOG"
echo "Press Ctrl+C to stop both services."

while true; do
  if ! kill -0 "$API_PID" >/dev/null 2>&1; then
    echo "FastAPI exited. Last log lines:"
    tail -n 40 "$API_LOG" || true
    exit 1
  fi
  if ! kill -0 "$WEB_PID" >/dev/null 2>&1; then
    echo "Next.js exited. Last log lines:"
    tail -n 40 "$WEB_LOG" || true
    exit 1
  fi
  sleep 1
done
