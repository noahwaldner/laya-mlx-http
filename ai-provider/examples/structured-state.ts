import { experimental_evaluate } from 'ai';
import { createLayaMlx } from '@noahwaldner/laya-mlx-http';

const layaMlxServe = createLayaMlx({
  baseURL: 'http://127.0.0.1:8000',
  apiKey: 'change-me',
});

// State, instructions and criteria can be objects; the adapter sends them as JSON.
const result = await experimental_evaluate({
  model: layaMlxServe.evaluationModel('laya-mlx'),
  state: {
    channel: 'email',
    from: 'cto@bigcorp.example',
    subject: 'Quote for 500 seats',
    body: 'Can we get a quote for 500 seats including SSO by Friday? Our board meets Monday.',
  },
  questions: {
    intent: {
      type: 'choice',
      instructions: {
        task: 'Classify the request in `body`',
        output: 'Pick the closest label',
      },
      criteria: {
        quote: { hint: 'Pricing or a formal offer' },
        support: { hint: 'A problem with an existing product' },
        partnership: null,
        other: null,
      },
    },
    seniority: {
      type: 'score',
      instructions: 'How senior does the sender in `from` appear to be?',
      criteria: ['Individual contributor', 'Manager', 'Executive'],
    },
    isSalesLead: {
      type: 'boolean',
      instructions: 'Is this a new sales opportunity?',
      criteria: {
        true: 'New business',
        false: 'Not sales related',
      },
    },
    hasDeadline: {
      type: 'boolean',
      instructions: 'Does `body` mention a concrete deadline?',
    },
  },
});

console.log('Answers:', result.answers);
console.log('Usage:', result.usage);
console.log('Raw response:', result.response.body);
