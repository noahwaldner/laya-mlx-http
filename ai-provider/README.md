# @noahwaldner/laya-mlx-http

AI SDK [evaluation provider](https://ai-sdk.dev/providers/ai-sdk-providers/typesafe-ai) for a
[`laya-mlx-http`](https://pypi.org/project/laya-mlx-http/) server: Choice, Score and Boolean
questions answered by a typed decision model running on Apple silicon.

It speaks plain HTTP to your own `laya-mlx-http` instance — machine A holds the model,
machine B (or C) just needs the URL.

## Setup

1. **Server** (Apple silicon, Python 3.11+):

   ```bash
   pip install laya-mlx-http
   laya-mlx-http --host 0.0.0.0 --api-key "$(openssl rand -hex 24)"
   ```

2. **Client** (any machine, Node 22+):

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
npm run example   # against a local laya-mlx-http on :8000
```

## License

Apache-2.0. See `LICENSE`.
