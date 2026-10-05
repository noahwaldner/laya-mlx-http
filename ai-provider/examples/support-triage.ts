import { experimental_evaluate } from 'ai';
import { createLayaMlx } from '@noahwaldner/laya-mlx-http';

const layaMlxServe = createLayaMlx({
  baseURL: 'http://127.0.0.1:8000',
  apiKey: 'change-me',
});

const result = await experimental_evaluate({
  model: layaMlxServe.evaluationModel('laya-mlx'),
  state: 'My access is not working even though i paid',
  questions: {
    department: {
      type: 'choice',
      instructions: 'Which team should handle this?',
      criteria: {
        billing: 'Charges and refunds',
        technical: 'Bugs and outages',
        other: null,
      },
    },
    severity: {
      type: 'score',
      instructions: 'How severe is the issue?',
      criteria: ['Cosmetic', 'Workaround exists', 'Blocking; no workaround'],
    },
    requestsRefund: {
      type: 'boolean',
      instructions: 'Is the customer requesting money back?',
    },
  },
});

console.log('Answers:', result.answers);
console.log('Usage:', result.usage);
console.log('Model:', result.response.modelId);
console.log('Provider metadata:', result.providerMetadata);
