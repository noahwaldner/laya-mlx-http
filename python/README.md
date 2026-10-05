# laya-mlx-http

HTTP server for [laya-mlx](https://pypi.org/project/laya-mlx/) typed decision models.
Runs the model once, keeps it in unified memory, and answers `POST /v1/predict`
requests from anything on your network.

**This package is only the server.** The API below is plain JSON over HTTP and is
client-agnostic — `curl`, Python, Node, a sensor, anything. No SDK is required.

The Vercel AI SDK integration is a *separate*, optional npm package,
[`@noahwaldner/laya-mlx-http`](https://www.npmjs.com/package/@noahwaldner/laya-mlx-http);
it translates AI SDK calls to and from this same API and is irrelevant if you are not
using the AI SDK.

Requires Apple silicon (MLX) and Python 3.11+.

## Install

```bash
uv tool install laya-mlx-http          # or: pip install laya-mlx-http
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
| `POST` | `/v1/predict` | `{"text": "...", "preset": "triage"}` or a full `questions` map |
| `GET` | `/v1/predict?text=...&preset=triage&flat=true` | same, for simple clients |

If `--api-key` is set, `/v1/*` requires `X-API-Key: <key>` (or `Authorization: Bearer <key>`).

## Predict format

This section is the **server's own wire format** — what goes over the wire no matter which
client sends it. It is not tied to any SDK.

If you are used to the AI SDK adapter, two names differ: its `state` is `text` here, and its
`boolean` is Laya's `noul`. Both translations happen client-side; the server only ever sees
`text`/`noul`. Full mapping:
[adapter README](https://github.com/noahwaldner/laya-mlx-http/tree/master/ai-provider#readme).

### Request

`POST /v1/predict` with a JSON body:

| Field | Type | Notes |
|---|---|---|
| `text` | string | **Required.** The state to classify (the message, ticket, …). |
| `questions` | object | Question map (below). Provide this **or** `preset`. |
| `preset` | string | One of the [bundled presets](#presets); only read when `questions` is absent. |
| `flat` | bool | Default `false`. Adds a `flat` map of question id → chosen value. |
| `model` | string | Optional. Echoed back as `model` in the response instead of the server's model id. |

`GET /v1/predict` takes the same call as query parameters: `text`, `preset`, `flat`, and
`questions` as a raw JSON **string** (`?questions={"a":{"type":"noul",...}}`, URL-encoded).

You must send `questions` or `preset` — otherwise `400`.

### Question map

```jsonc
{
  "department": {
    "type": "choice",                                  // choice | score | noul
    "instructions": "Which team should handle this?",  // required, non-blank
    "criteria": {                                      // shape depends on type
      "billing": "Charges and refunds",
      "support": "Other requests"
    }
  }
}
```

- `instructions` — required and must not be blank. A string, or any JSON-serializable
  object/array (it is serialized to JSON before it reaches the model).
- `type: "choice"` — `criteria` required: a non-empty `{label: description}` object
  (or an array of unique labels; descriptions may be `null`). Returns the winning label
  plus full probabilities.
- `type: "score"` — `criteria` required: a non-empty, **ordered** array of level
  descriptions (e.g. `["calm", "annoyed", "very angry"]`). Returns a 0-based expected score.
- `type: "noul"` — Laya's boolean. `criteria` optional: `{"false": "...", "true": "..."}`.
  Returns a probability in `[0, 1]` for `true`.

### Response

```jsonc
{
  "model": "aac6fef/laya-mlx",
  "answers": {
    "department": {
      "type": "choice",
      "choice": "billing",
      "probabilities": { "billing": 0.91, "support": 0.09 },
      "confidence": 0.91, "answer_confidence": 0.91,
      "action": { "act_probability": 0.42 }
    },
    "frustration": {
      "type": "score",
      "score": 1.64,
      "legend": { "0": "calm", "1": "annoyed", "2": "very angry" },
      "probabilities": { "0": 0.1, "1": 0.5, "2": 0.4 },
      "confidence": 0.5, "answer_confidence": 0.5,
      "action": { "act_probability": 0.42 }
    },
    "is_urgent": {
      "type": "noul",
      "noul": 0.42,
      "confidence": 0.58, "answer_confidence": 0.58,
      "action": { "act_probability": 0.42 }
    }
  },
  "flat": { "department": "billing", "frustration": 1.64, "is_urgent": 0.42 },
  "usage": {
    "input_tokens": 512, "output_tokens": 0,
    "state_tokens": 480, "state_tokens_dropped": 0,
    "truncated": false, "truncated_questions": []
  }
}
```

`flat` only appears with `"flat": true`. Probabilities, scores and confidences are rounded to
4 decimals. `usage.truncated` is `true` when input tokens had to be dropped to fit the model's
context limit; the affected question ids are in `truncated_questions`.

### Errors

| Status | When |
|---|---|
| `400` | Neither `questions` nor `preset`; unknown `preset` (the message lists valid names); invalid `questions` JSON on `GET`; any model-side validation error (empty `instructions`, bad `criteria`, …). |
| `401` | `--api-key` set and the key is missing/wrong. |
| `503` | Model not loaded yet (server still starting). |

### Example

```bash
curl -s http://127.0.0.1:8000/v1/predict \
  -H 'content-type: application/json' -H 'X-API-Key: ...' \
  -d '{"text": "I was charged twice, please refund", "preset": "triage", "flat": true}'
```

## Presets

`preset` is a shortcut for a ready-made question map. It is a **server-side** feature: any
HTTP client can send it (the AI SDK adapter does not expose it — it always sends an explicit
`questions` map). Bundled names:

| Name | What it answers |
|---|---|
| `triage` | intent, urgency, frustration, refund request, churn risk (support tickets) |
| `email` | team/category routing, spam, phishing, urgency, reply expected |
| `guard` | jailbreak, prompt injection, sensitive data, harm severity, topic |
| `moderation` | toxicity, harassment, threats, spam, violation severity |
| `router` | difficulty, domain, needs tools, sensitive (money/legal/medical/safety) |

The definitions live in the [`laya-mlx`](https://pypi.org/project/laya-mlx/) package; dump
any of them as JSON:

```bash
python -c "import json, laya_mlx; print(json.dumps(laya_mlx.triage_questions(), indent=2))"
```

The API accepts only the preset *names* — the definitions themselves are not served over
HTTP. Dump one as above and pass it back as `questions` if you want to edit it first.

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

Embed the **server** in your own Python process. This is the ASGI app, not a client SDK —
from Python you can also skip HTTP entirely and call
[`laya_mlx`](https://pypi.org/project/laya-mlx/) directly (`agent.predict(text, questions)`).

```python
from laya_mlx_http import create_app, Settings

app = create_app(Settings(host="127.0.0.1", port=8000, api_key="…"))
# uvicorn laya_mlx_http:app   ← runs with default settings (127.0.0.1:8000)
```

## License

Apache-2.0. See `NOTICE` in the repository.
