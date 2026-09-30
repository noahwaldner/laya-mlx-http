import { experimental_evaluate } from 'ai';
import { layaMlx } from '../dist/index.js';

const result = await experimental_evaluate({
  model: layaMlx.evaluationModel('laya-mlx'),
  state: 'I was charged twice for the same order and I want the duplicate charge back.',
  questions: {
    department: {
      type: 'choice',
      instructions: 'Which team should handle this?',
      criteria: {
        billing: 'Charges, invoices and refunds',
        support: 'Product and technical problems',
      },
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

console.log(
  JSON.stringify(
    {
      answers: result.answers,
      usage: result.usage,
      confidence: result.providerMetadata,
      model: result.response.modelId,
    },
    null,
    2,
  ),
);
