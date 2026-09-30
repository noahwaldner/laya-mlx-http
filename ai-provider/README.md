# laya-mlx

AI SDK [evaluation provider](https://ai-sdk.dev/providers/ai-sdk-providers/typesafe-ai) for a
[`laya-mlx`](https://pypi.org/project/laya-mlx/) server: Choice, Score and Boolean questions
answered by a typed decision model running on Apple silicon.

It speaks plain HTTP to your own `laya-mlx-serve` instance — machine A holds the model,
machine B (or C, or your Home Assistant box) just needs the URL.

## Setup

1. **Server** (Apple silicon):

   ```bash
   pip install laya-mlx-serve
   laya-mlx-serve --host 0.0.0.0 --api-key "$(openssl rand -hex 24)"
   ```

2. **Client** (any machine):

   ```bash
   npm install laya-mlx ai zod
   ```

## Usage

```ts
import { experimental_evaluate } from 'ai';
import { createLayaMlx, layaMlx } from 'laya-mlx';

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
  baseURL: 'http://mac-mini.local:8000',
  apiKey: process.env.LAYA_MLX_API_KEY, // optional; only if the server runs with --api-key
});
```

or purely via environment:

```bash
LAYA_MLX_BASE_URL=http://mac-mini.local:8000
LAYA_MLX_API_KEY=...
```

### Options

| Option | Environment variable | Default |
| --- | --- | --- |
| `baseURL` | `LAYA_MLX_BASE_URL` | `http://127.0.0.1:8000` |
| `apiKey` (sent as `X-API-Key`) | `LAYA_MLX_API_KEY` | none |
| `headers` | — | none |
| `fetch` | — | global `fetch` |

## What gets sent

- `state` — a string is sent as-is; objects/arrays are `JSON.stringify`-ed.
- Questions are translated from AI SDK vocabulary to Laya's: `boolean` → `noul`,
  structured `instructions`/criteria become JSON text, `null` criteria stay "no description".
- Answers come back as `choice` / `score` / `boolean` (from `noul`) with the full probability
  distribution. The server rounds to 4 decimals and the provider declares that rounding.
- Per-question model confidence is exposed as
  `result.providerMetadata.layaMlx.confidence[questionId]`.

This provider only implements the evaluation model: `languageModel()`, `embeddingModel()` and
`imageModel()` throw `NoSuchModelError` — Laya answers questions, it does not generate text.

## Development

```bash
npm install
npm test          # vitest, stubbed fetch
npm run build
npm run example   # against a local laya-mlx-serve on :8000
```

## License

Apache-2.0. See `LICENSE`.
