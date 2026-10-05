# laya-mlx-http

HTTP server for [laya-mlx](https://pypi.org/project/laya-mlx/) typed decision models.
Runs the model once, keeps it in unified memory, and answers `POST /v1/predict`
requests from anything on your network — the companion
[`@noahwaldner/laya-mlx-http`](https://www.npmjs.com/package/@noahwaldner/laya-mlx-http)
npm provider or plain `curl`.

Requires Apple silicon (MLX) and Python 3.11+.

## Install

```bash
pip install laya-mlx-http          # or: uv tool install laya-mlx-http
```

## Run

```bash
# localhost only (default, safest)
laya-mlx-http

# expose on your LAN — always set an API key
laya-mlx-http --host 0.0.0.0 --api-key "$(openssl rand -hex 24)"
```

Then from another machine:

```bash
curl http://<server-ip>:8000/health
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | liveness + model readiness (never authenticated) |
| `GET` | `/v1/presets` | bundled question sets (`triage`, `email`, `guard`, `moderation`, `router`) |
| `POST` | `/v1/predict` | `{"text": "...", "preset": "triage"}` or a full `questions` map |
| `GET` | `/v1/predict?text=...&preset=triage&flat=true` | same, for simple clients |

If `--api-key` is set, `/v1/*` requires `X-API-Key: <key>` (or `Authorization: Bearer <key>`).

## Run at login (launchd, macOS)

```bash
laya-mlx-http install --host 0.0.0.0 --api-key "$KEY"   # write + load a user agent
laya-mlx-http start | stop | status | logs | uninstall
```

No sudo, no hand-edited system files; the plist lives in `~/Library/LaunchAgents`.

## Configuration

Flags only — nothing is read from the environment or a config file:

| Flag | Default |
|---|---|
| `--host` | `127.0.0.1` |
| `--port` | `8000` |
| `--api-key` | unset (no auth) |
| `--model` | `aac6fef/laya-mlx` |
| `--dtype` | `float16` |

## Library use

```python
from laya_mlx_http import create_app, Settings

app = create_app(Settings(host="127.0.0.1", port=8000, api_key="…"))
# uvicorn laya_mlx_http:app   ← runs with default settings (127.0.0.1:8000)
```

## License

Apache-2.0. See `NOTICE` in the repository.
