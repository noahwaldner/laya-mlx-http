# laya-mlx-http + AI SDK provider

Run a [laya-mlx](https://pypi.org/project/laya-mlx/) typed-decision model once on an Apple
silicon machine, then call it over HTTP from anywhere — including from the Vercel AI SDK via
`experimental_evaluate`.

```
┌──────────────────────────┐         HTTP          ┌─────────────────────────────┐
│  any machine             │  POST /v1/predict     │  Apple silicon Mac          │
│  ai agents / scripts /    │ ────────────────────► │  laya-mlx-http             │
│  curl + npm package      │   X-API-Key: …        │  model kept in unified mem  │
└──────────────────────────┘                       └─────────────────────────────┘
```

Two packages, one repo:

| Package | Registry | What it is |
| --- | --- | --- |
| [`laya-mlx-http`](python/) | PyPI | the HTTP server (`laya-mlx-http` CLI) |
| [`@noahwaldner/laya-mlx-http`](ai-provider/) | npm | AI SDK evaluation provider (`layaMlx.evaluationModel()`) |

## Quickstart

**On the machine with the GPU:**

```bash
pip install laya-mlx-http

# localhost only (default)
laya-mlx-http

# or serve your LAN — always pair exposure with a key
laya-mlx-http --host 0.0.0.0 --api-key "$(openssl rand -hex 24)"
```

**On the machine writing code:**

```bash
npm install @noahwaldner/laya-mlx-http ai zod
```

```ts
import { experimental_evaluate } from 'ai';
import { createLayaMlx } from '@noahwaldner/laya-mlx-http';

const laya = createLayaMlx({
  baseURL: 'http://my-server.local:8000', // your server
  apiKey: 'your-key',                     // omit if the server has no --api-key
});

const result = await experimental_evaluate({
  model: laya.evaluationModel('laya-mlx'),
  state: 'I was charged twice. Please refund the duplicate.',
  questions: {
    department: {
      type: 'choice',
      instructions: 'Which team should handle this?',
      criteria: { billing: 'Charges and refunds', support: 'Other requests' },
    },
    requestsRefund: {
      type: 'boolean',
      instructions: 'Is the customer requesting money back?',
    },
  },
});
```

More options, mapping details and a full example: [`ai-provider/README.md`](ai-provider/README.md).

## Keeping it running (no sudo, no hand-edited system files)

```bash
laya-mlx-http install --host 0.0.0.0 --api-key "$KEY"   # launchd user agent
laya-mlx-http start | stop | status | logs | uninstall
```

The agent lives in `~/Library/LaunchAgents/laya-mlx-http.plist`, starts at login and
restarts on crash. For local development there is also [`ctl.sh`](ctl.sh)
(`./ctl.sh start|stop|status|logs`, pidfile in `run/`).

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | liveness + readiness, never authenticated |
| `GET` | `/v1/presets` | bundled question sets: `triage`, `email`, `guard`, `moderation`, `router` |
| `POST` | `/v1/predict` | `{"text": "…", "preset": "triage", "flat": true}` or a full `questions` map |
| `GET` | `/v1/predict?text=…&preset=triage&flat=true` | same, for simple clients (sensors, curl) |

With `--api-key` set, `/v1/*` requires `X-API-Key: <key>` (or `Authorization: Bearer <key>`).

## Security notes

- Default bind is `127.0.0.1`. Use `--host 0.0.0.0` **only** together with `--api-key`
  (the installer refuses to install a LAN-exposed agent without one).
- macOS may show a firewall prompt on first start — allow incoming connections for Python
  if you want other machines to reach it.
- The API key ends up in the launchd plist, which is written mode `0600`.

## Repository layout

```
python/           PyPI package laya-mlx-http (FastAPI app, CLI, launchd, tests)
ai-provider/      npm package @noahwaldner/laya-mlx-http (AI SDK provider, tests, examples)
.github/          CI + release workflows (tag a version → publish both packages)
scripts/          version sync helper used by releases and CI
Makefile          setup / test / build / bump entry points
RELEASING.md      how to cut a release
ctl.sh            local dev start/stop helper
```

## Development

```bash
make setup    # uv venv + python deps + npm install
make test     # pytest + vitest + type-check
make build    # wheel/sdist + npm dist (pack preview)

# live end-to-end (model must be loaded)
./ctl.sh start && (cd ai-provider && npm run example)
```

Without `make`, the Python side is:

```bash
uv venv && uv pip install -e './python[dev]' --python .venv/bin/python
.venv/bin/python -m pytest python/tests
```

## Releasing

See [`RELEASING.md`](RELEASING.md): bump the version, tag `vX.Y.Z`, push —
[GitHub Actions](.github/workflows/release.yml) publishes both packages to
PyPI and npm (one-time publisher setup documented there).

## License

Apache-2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
