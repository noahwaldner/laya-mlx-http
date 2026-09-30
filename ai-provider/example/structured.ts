import { experimental_evaluate } from 'ai';
import { layaMlx } from '../dist/index.js';

const result = await experimental_evaluate({
  model: layaMlx.evaluationModel('laya-mlx'),
  state: {
    channel: 'email',
    from: 'ceo@example.com',
    body: 'Can we get a quote for 500 seats by Friday?',
  },
  questions: {
    intent: {
      type: 'choice',
      instructions: {
        task: 'Classify the request',
        output: 'pick the closest label',
      },
      criteria: {
        quote: { hint: 'pricing or a formal offer' },
        support: null,
      },
    },
    is_sales: {
      type: 'boolean',
      instructions: 'Is this a sales opportunity?',
      criteria: { true: 'new business', false: 'not sales' },
    },
    urgency: {
      type: 'score',
      instructions: 'How urgent is it?',
      criteria: ['relaxed', 'soon', 'friday deadline'],
    },
  },
});

console.log(JSON.stringify(result.answers, null, 2));
console.log('provider:', result.response.modelId, 'tokens:', result.usage.inputTokens);
