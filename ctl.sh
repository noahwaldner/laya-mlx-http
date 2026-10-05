#!/usr/bin/env bash
# Dev convenience: start/stop the API in the background with a pidfile.
# For a real deployment use `laya-mlx-http install` (launchd) instead.
#
# All configuration is explicit: flags after the command are forwarded to
# laya-mlx-http. No environment variables and no .env files are read.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

RUN_DIR="$PWD/run"
PID_FILE="$RUN_DIR/server.pid"
LOG_FILE="$RUN_DIR/server.log"
READY_TIMEOUT=300
SERVE="$PWD/.venv/bin/laya-mlx-http"

# Tracked from the forwarded flags so readiness checks hit the right port.
HOST=127.0.0.1
PORT=8000

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
  curl -fsS --max-time 3 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -Eq '"ready"[[:space:]]*:[[:space:]]*true'
}

track_flags() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --host)   HOST="${2:?--host needs a value}"; shift 2 ;;
      --host=*) HOST="${1#--host=}"; shift ;;
      --port)   PORT="${2:?--port needs a value}"; shift 2 ;;
      --port=*) PORT="${1#--port=}"; shift ;;
      *)        shift ;;
    esac
  done
}

start() {
  if [ ! -x "$SERVE" ]; then
    echo "error: $SERVE is missing." >&2
    echo "Run 'make setup' first (or: uv venv && uv pip install -e './python[dev]' --python .venv/bin/python)." >&2
    exit 1
  fi
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
  "$SERVE" "$@" >>"$LOG_FILE" 2>&1 &
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
  echo "local:   http://127.0.0.1:${PORT}"
  echo "lan:     http://$(lan_ip):${PORT}"
  echo "log:     $LOG_FILE"
}

CMD="${1:-}"
case "$CMD" in
  start|stop|restart|status|logs) ;;
  *)
    cat <<EOF
usage: $0 {start|stop|restart|status|logs} [server flags]

  start    launch the server in the background, wait until the model is loaded
  stop     graceful stop (SIGTERM, then SIGKILL after 20s)
  restart  stop + start
  status   pid, readiness, urls
  logs     follow $LOG_FILE

Flags after the command are forwarded to laya-mlx-http, e.g.:
  $0 start --host 0.0.0.0 --api-key "\$(openssl rand -hex 24)" --model some/model

Defaults: 127.0.0.1:8000. Nothing is read from the environment or a .env file.

This script is for local development; production boxes should use:
  laya-mlx-http install   (launchd user agent, survives reboots)
EOF
    exit 1 ;;
esac
shift
track_flags "$@"

case "$CMD" in
  start)   start "$@" ;;
  stop)    stop ;;
  restart) stop; start "$@" ;;
  status)  status ;;
  logs)    mkdir -p "$RUN_DIR"; touch "$LOG_FILE"; exec tail -n 100 -f "$LOG_FILE" ;;
esac
