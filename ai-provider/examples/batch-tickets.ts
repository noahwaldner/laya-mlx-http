import { experimental_evaluate } from 'ai';
import { createLayaMlx } from '@noahwaldner/laya-mlx-http';

const layaMlxServe = createLayaMlx({
  baseURL: 'http://127.0.0.1:8000',
  apiKey: 'change-me',
});

const tickets = [
  'Production API returns 500 for every request since 9am. We are completely down!',
  "Could you send me last month's invoice as PDF? Thanks a lot.",
  'I forgot my password and the reset email never arrives.',
  'What does the Enterprise plan cost for 50 users?',
  'Charged twice AGAIN. Considering switching to another vendor if this keeps happening.',
];

const results = await Promise.all(
  tickets.map(ticket =>
    experimental_evaluate({
      model: layaMlxServe.evaluationModel('laya-mlx'),
      state: ticket,
      questions: {
        queue: {
          type: 'choice',
          instructions: 'Which queue should the ticket go to?',
          criteria: {
            billing: 'Invoices, charges and refunds',
            technical: 'Bugs, outages and errors',
            account: 'Login, password and permissions',
            sales: 'Pricing and new purchases',
          },
        },
        urgent: {
          type: 'boolean',
          instructions: 'Is there time pressure or a blocking problem?',
        },
        churnRisk: {
          type: 'boolean',
          instructions: 'Might the customer cancel or switch to a competitor?',
        },
      },
    }),
  ),
);

console.table(
  results.map((result, i) => ({
    ticket: tickets[i]!.slice(0, 50),
    queue: result.answers.queue.choice,
    urgent: result.answers.urgent.probability,
    churnRisk: result.answers.churnRisk.probability,
  })),
);
