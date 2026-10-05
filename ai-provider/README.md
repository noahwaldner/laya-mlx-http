# @noahwaldner/laya-mlx-http

AI SDK [evaluation provider](https://ai-sdk.dev/providers/ai-sdk-providers/typesafe-ai) for a
[`laya-mlx-http`](https://pypi.org/project/laya-mlx-http/) server: Choice, Score and Boolean
questions answered by a typed decision model running on Apple silicon.

**This package is only the adapter.** It holds no model and serves no HTTP — it turns
`experimental_evaluate` calls into `POST /v1/predict` requests and maps the answers back.
The server is the Python package `laya-mlx-http`; its API is documented in the
[`python/README.md` "Predict format" section](https://github.com/noahwaldner/laya-mlx-http/blob/master/python/README.md#predict-format).
You do not need this adapter to use the server: any HTTP client can call the API directly.

It speaks plain HTTP to your own `laya-mlx-http` instance — machine A holds the model,
machine B (or C) just needs the URL.

## Setup

1. **Server** (Apple silicon, Python 3.11+):

   ```bash
   uv tool install laya-mlx-http
   laya-mlx-http --host 0.0.0.0 --api-key "$(openssl rand -hex 24)"
   ```

2. **Client — only needed for the AI SDK** (any machine, Node 22+):

   ```bash
   npm install @noahwaldner/laya-mlx-http ai zod
   ```

## Usage

```ts
import { experimental_evaluate } from 'ai';
import { createLayaMlx, layaMlx } from '@noahwaldner/laya-mlx-http';

const result = await experimental_evaluate({
  model: layaMlx.evaluationModel('laya-mlx'),
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
    urgency: {
      type: 'score',
      instructions: 'How urgent is the message?',
      criteria: ['no time pressure', 'needs attention soon', 'blocking issue'],
    },
  },
});

console.log(result.answers);
// { department: { type: 'choice', choice: 'billing', probabilities: {...} },
//   requestsRefund: { type: 'boolean', probability: 0.86 },
//   urgency: { type: 'score', score: 1.64, probabilities: {...} } }
```

### Pointing it at your AI server

```ts
const laya = createLayaMlx({
  baseURL: 'http://localhost:8000',
  apiKey: 'your-key', // optional; must match the server's --api-key, passed explicitly
});
```

### Options

| Option | Default |
| --- | --- |
| `baseURL` | `http://127.0.0.1:8000` |
| `apiKey` (sent as `X-API-Key`) | none (must be passed explicitly) |
| `headers` | none |
| `fetch` | global `fetch` |

No environment variables are read; configuration is explicit only.

## Adapter vs the raw API

The table below is everything this package does beyond talking HTTP. The server itself only
ever sees the wire format in
[`python/README.md`](https://github.com/noahwaldner/laya-mlx-http/blob/master/python/README.md#predict-format).

| AI SDK side (this adapter) | On the wire (`POST /v1/predict`) |
| --- | --- |
| `state` — string, or object/array | `text` — string (objects/arrays are `JSON.stringify`-ed) |
| question type `boolean` | `type: "noul"` (Laya's boolean primitive) |
| structured `instructions` / criteria | JSON text (the server wants text) |
| answer `type: "boolean"`, `probability` | answer `type: "noul"`, `noul` |
| `choice` / `score` answers + `probabilities` | passed through unchanged |
| `null` criterion description | `null` for choice/boolean, `""` for score levels (avoids `level N: null`) |
| `providerMetadata.layaMlx.confidence[qid]` | `answers[qid].confidence` |
| `usage.inputTokens` / `usage.outputTokens` | `usage.input_tokens` / `usage.output_tokens` (token/truncation detail stays in `result.response.body`) |
| declared rounding (4 decimals) | server rounds probabilities/scores/confidence to 4 decimals |
| `modelId` | `model` (echo override; the response's `model` is surfaced as `response.modelId`) |

Server features this adapter deliberately does **not** expose — use the raw API for them:

- `preset` — `providerOptions.layaMlx.preset` produces an `unsupported` warning and is
  ignored; always send an explicit `questions` map, or call the server directly;
- `flat` (the flat answer map) and the `GET /v1/predict` query-string variant.

This provider only implements the evaluation model: `languageModel()`, `embeddingModel()` and
`imageModel()` throw `NoSuchModelError` — Laya answers questions, it does not generate text.

## Development

```bash
npm install
npm test          # vitest, stubbed fetch
npm run build
npm run example   # against a local laya-mlx-http on :8000
```

## License

Apache-2.0. See `LICENSE`.
