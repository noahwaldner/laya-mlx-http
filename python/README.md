# laya-mlx-serve

HTTP server for [laya-mlx](https://pypi.org/project/laya-mlx/) typed decision models.
Runs the model once, keeps it in unified memory, and answers `POST /v1/predict`
requests from anything on your network — the companion
[`laya-mlx`](https://www.npmjs.com/package/laya-mlx) npm provider, Home Assistant,
or plain `curl`.

Requires Apple silicon (MLX).

## Install

```bash
pip install laya-mlx-serve          # or: uv tool install laya-mlx-serve
```

## Run

```bash
# localhost only (default, safest)
laya-mlx-serve

# expose on your LAN — always set an API key
laya-mlx-serve --host 0.0.0.0 --api-key "$(openssl rand -hex 24)"
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
laya-mlx-serve install --host 0.0.0.0 --api-key "$KEY"   # write + load a user agent
laya-mlx-serve start | stop | status | logs | uninstall
```

No sudo, no hand-edited system files; the plist lives in `~/Library/LaunchAgents`.

## Configuration

Flags override environment variables:

| Flag | Environment variable | Default |
|---|---|---|
| `--host` | `LAYA_MLX_HOST` | `127.0.0.1` |
| `--port` | `LAYA_MLX_PORT` | `8000` |
| `--api-key` | `LAYA_MLX_API_KEY` | unset (no auth) |
| `--model` | `LAYA_MLX_MODEL_ID` | `aac6fef/laya-mlx` |
| `--dtype` | `LAYA_MLX_DTYPE` | `float16` |

## Library use

```python
from laya_mlx_serve import create_app, Settings

app = create_app(Settings(host="127.0.0.1", port=8000, api_key="…"))
# uvicorn laya_mlx_serve:app   ← env-configured instance
```

## License

Apache-2.0. See `NOTICE` in the repository.
