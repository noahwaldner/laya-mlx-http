#!/usr/bin/env bash
# Dev convenience: start/stop the API in the background with a pidfile.
# For a real deployment use `laya-mlx-serve install` (launchd) instead.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

RUN_DIR="$PWD/run"
PID_FILE="$RUN_DIR/server.pid"
LOG_FILE="$RUN_DIR/server.log"
HOST="${LAYA_MLX_HOST:-127.0.0.1}"
PORT="${LAYA_MLX_PORT:-8000}"
READY_TIMEOUT="${READY_TIMEOUT:-300}"
SERVE="$PWD/.venv/bin/laya-mlx-serve"
BASE_URL="http://127.0.0.1:${PORT}"
export LAYA_MLX_HOST LAYA_MLX_PORT
if [ -n "${LAYA_MLX_API_KEY:-}" ]; then export LAYA_MLX_API_KEY; fi
if [ -n "${LAYA_MLX_MODEL_ID:-}" ]; then export LAYA_MLX_MODEL_ID; fi

pid() {
  [ -f "$PID_FILE" ] || return 1
  local p
  p="$(cat "$PID_FILE" 2>/dev/null || true)"
  [ -n "$p" ] || return 1
  kill -0 "$p" 2>/dev/null || return 1
  echo "$p"
}

lan_ip() {
  ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost"
}

port_busy() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1
}

ready() {
  curl -fsS --max-time 3 "$BASE_URL/health" 2>/dev/null | grep -Eq '"ready"[[:space:]]*:[[:space:]]*true'
}

start() {
  if p="$(pid)"; then
    echo "already running (pid $p, port $PORT)"
    return 0
  fi
  rm -f "$PID_FILE"
  if port_busy; then
    echo "error: port $PORT is already in use by another process:" >&2
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
    exit 1
  fi
  mkdir -p "$RUN_DIR"
  echo "starting server (host $HOST, port $PORT) ..."
  "$SERVE" >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  p="$(pid)"
  echo "pid $p, log $LOG_FILE"
  echo -n "waiting for model to load"
  local waited=0
  while [ "$waited" -lt "$READY_TIMEOUT" ]; do
    if ! pid >/dev/null; then
      echo ""
      echo "error: server exited during startup, last log lines:" >&2
      tail -n 30 "$LOG_FILE" >&2 || true
      exit 1
    fi
    if ready; then
      echo ""
      echo "ready: http://$(lan_ip):${PORT}  (docs: /docs)"
      return 0
    fi
    sleep 2
    waited=$((waited + 2))
    echo -n "."
  done
  echo ""
  echo "warning: model not ready after ${READY_TIMEOUT}s, server still running (see $LOG_FILE)" >&2
  exit 1
}

stop() {
  local p
  if ! p="$(pid)"; then
    echo "not running"
    rm -f "$PID_FILE"
    return 0
  fi
  echo "stopping pid $p ..."
  kill -TERM "$p" 2>/dev/null || true
  local i=0
  while [ "$i" -lt 20 ] && kill -0 "$p" 2>/dev/null; do
    sleep 1
    i=$((i + 1))
  done
  if kill -0 "$p" 2>/dev/null; then
    echo "still alive after 20s, sending SIGKILL"
    kill -KILL "$p" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PID_FILE"
  echo "stopped"
}

status() {
  local p state
  if ! p="$(pid)"; then
    echo "stopped"
    return 1
  fi
  if ready; then state="ready"; else state="starting / unhealthy"; fi
  echo "running: pid $p, state $state"
  echo "local:   $BASE_URL"
  echo "lan:     http://$(lan_ip):${PORT}"
  echo "log:     $LOG_FILE"
}

case "${1:-}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  logs)    mkdir -p "$RUN_DIR"; touch "$LOG_FILE"; exec tail -n 100 -f "$LOG_FILE" ;;
  *)
    cat <<EOF
usage: $0 {start|stop|restart|status|logs}

  start    launch the server in the background, wait until the model is loaded
  stop     graceful stop (SIGTERM, then SIGKILL after 20s)
  restart  stop + start
  status   pid, readiness, urls
  logs     follow $LOG_FILE

Config comes from a .env file (see examples/.env.example) or the environment:
  LAYA_MLX_HOST  LAYA_MLX_PORT  LAYA_MLX_API_KEY  LAYA_MLX_MODEL_ID  READY_TIMEOUT

This script is for local development; production boxes should use:
  laya-mlx-serve install   (launchd user agent, survives reboots)
EOF
    exit 1 ;;
esac
