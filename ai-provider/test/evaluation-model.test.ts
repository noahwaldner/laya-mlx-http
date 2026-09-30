import { NoSuchModelError } from '@ai-sdk/provider';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLayaMlx, layaMlx } from '../src/index.js';

type Recorded = { url: string; headers: Record<string, string>; body: any };

function stubFetch(reply: { status?: number; body: unknown }) {
  const calls: Recorded[] = [];
  const fetchFn = async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers: Record<string, string> = {};
    new Headers(init?.headers).forEach((value, key) => {
      headers[key.toLowerCase()] = value;
    });
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) : undefined;
    calls.push({ url: String(input), headers, body });
    return new Response(JSON.stringify(reply.body), {
      status: reply.status ?? 200,
      headers: { 'content-type': 'application/json' },
    });
  };
  return { fetch: fetchFn as typeof fetch, calls };
}

const okReply = {
  body: {
    model: 'aac6fef/laya-mlx',
    answers: {
      department: {
        type: 'choice',
        choice: 'billing',
        probabilities: { billing: 0.9236, support: 0.0764 },
        confidence: 0.6105,
      },
      is_urgent: { type: 'noul', noul: 0.2, confidence: 0.8 },
      urgency: {
        type: 'score',
        score: 1.6394,
        probabilities: { '0': 0.0453, '1': 0.2701, '2': 0.6846 },
        confidence: 0.3145,
      },
    },
    usage: { input_tokens: 145, output_tokens: 0 },
  },
};

function evaluate(model: any, options: Record<string, unknown> = {}) {
  return model.doEvaluate({
    state: 'I was charged twice.',
    questions: {
      department: {
        type: 'choice',
        instructions: 'Which team?',
        criteria: { billing: 'Charges', support: 'Other' },
      },
      is_urgent: { type: 'boolean', instructions: 'Is this urgent?' },
      urgency: {
        type: 'score',
        instructions: 'How urgent?',
        criteria: ['relaxed', 'soon', 'blocking'],
      },
    },
    ...options,
  });
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('createLayaMlx', () => {
  it('posts to {baseURL}/v1/predict and strips a trailing slash', async () => {
    const { fetch, calls } = stubFetch(okReply);
    const model = createLayaMlx({
      baseURL: 'http://mac-mini:8000/',
      fetch,
    }).evaluationModel('laya-mlx');

    await evaluate(model);

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('http://mac-mini:8000/v1/predict');
    expect(calls[0].body.model).toBe('laya-mlx');
    expect(calls[0].body.text).toBe('I was charged twice.');
  });

  it('reads LAYA_MLX_BASE_URL from the environment', async () => {
    vi.stubEnv('LAYA_MLX_BASE_URL', 'http://env-host:9000');
    const { fetch, calls } = stubFetch(okReply);
    const model = createLayaMlx({ fetch }).evaluationModel('laya-mlx');

    await evaluate(model);

    expect(calls[0].url).toBe('http://env-host:9000/v1/predict');
  });

  it('sends X-API-Key only when a key is configured', async () => {
    const withKey = stubFetch(okReply);
    const withoutKey = stubFetch(okReply);

    await evaluate(
      createLayaMlx({ apiKey: 's3cret', fetch: withKey.fetch }).evaluationModel('x'),
    );
    await evaluate(
      createLayaMlx({ fetch: withoutKey.fetch }).evaluationModel('x'),
    );

    expect(withKey.calls[0].headers['x-api-key']).toBe('s3cret');
    expect(withoutKey.calls[0].headers['x-api-key']).toBeUndefined();
    expect(withKey.calls[0].headers['user-agent']).toMatch(/^ai-sdk-laya-mlx\//);
  });

  it('keeps user-supplied headers', async () => {
    const { fetch, calls } = stubFetch(okReply);
    const model = createLayaMlx({
      headers: { 'X-Trace': 'abc' },
      fetch,
    }).evaluationModel('x');

    await evaluate(model);

    expect(calls[0].headers['x-trace']).toBe('abc');
  });
});

describe('question mapping', () => {
  it('converts boolean questions to noul and serializes structured input', async () => {
    const { fetch, calls } = stubFetch(okReply);
    const model = createLayaMlx({ fetch }).evaluationModel('x');

    await model.doEvaluate({
      state: { channel: 'email', body: 'please refund' },
      questions: {
        is_refund: {
          type: 'boolean',
          instructions: { task: 'judge' },
          criteria: { true: 'asks for money back', false: null },
        },
        intent: {
          type: 'choice',
          instructions: 'Classify',
          criteria: { quote: { hint: 'pricing' }, support: null },
        },
        urgency: {
          type: 'score',
          instructions: 'How urgent?',
          criteria: ['relaxed', null, 'friday deadline'],
        },
      },
    });

    const questions = calls[0].body.questions;
    expect(calls[0].body.text).toBe(JSON.stringify({ channel: 'email', body: 'please refund' }));
    expect(questions.is_refund.type).toBe('noul');
    expect(questions.is_refund.instructions).toBe(JSON.stringify({ task: 'judge' }));
    expect(questions.is_refund.criteria).toEqual({
      true: 'asks for money back',
      false: null,
    });
    expect(questions.intent.criteria).toEqual({
      quote: JSON.stringify({ hint: 'pricing' }),
      support: null,
    });
    // null levels stay empty rather than rendering as "null"
    expect(questions.urgency.criteria).toEqual(['relaxed', '', 'friday deadline']);
  });

  it('rejects choice questions with more than 255 options', async () => {
    const { fetch } = stubFetch(okReply);
    const model = createLayaMlx({ fetch }).evaluationModel('x');
    const criteria = Object.fromEntries(
      Array.from({ length: 256 }, (_, i) => [`opt${i}`, null]),
    );

    await expect(
      model.doEvaluate({
        state: 'x',
        questions: { q: { type: 'choice', instructions: 'pick', criteria } },
      }),
    ).rejects.toThrow(/at most 255/);
  });
});

describe('answer mapping', () => {
  it('maps noul answers to boolean probabilities and reports usage', async () => {
    const { fetch } = stubFetch(okReply);
    const model = createLayaMlx({ fetch }).evaluationModel('x');

    const result = await evaluate(model);

    expect(result.answers).toEqual({
      department: {
        type: 'choice',
        choice: 'billing',
        probabilities: { billing: 0.9236, support: 0.0764 },
      },
      is_urgent: { type: 'boolean', probability: 0.2 },
      urgency: {
        type: 'score',
        score: 1.6394,
        probabilities: { '0': 0.0453, '1': 0.2701, '2': 0.6846 },
      },
    });
    expect(result.usage).toEqual({ inputTokens: 145, outputTokens: 0 });
    expect(result.rounding).toEqual({
      probabilityDecimals: 4,
      scoreDecimals: 4,
    });
    expect(result.providerMetadata).toEqual({
      layaMlx: { confidence: { department: 0.6105, is_urgent: 0.8, urgency: 0.3145 } },
    });
    expect(result.response?.modelId).toBe('aac6fef/laya-mlx');
    expect(result.warnings).toEqual([]);
  });

  it('falls back to the requested model id when the server omits it', async () => {
    const { fetch } = stubFetch({
      body: { answers: { q: { type: 'noul', noul: 0.5 } } },
    });
    const model = createLayaMlx({ fetch }).evaluationModel('laya-mlx');

    const result = await evaluate(model, {
      questions: { q: { type: 'boolean', instructions: 'ok?' } },
    });

    expect(result.response?.modelId).toBe('laya-mlx');
  });

  it('warns about unsupported provider options', async () => {
    const { fetch } = stubFetch(okReply);
    const model = createLayaMlx({ fetch }).evaluationModel('x');

    const result = await evaluate(model, {
      providerOptions: { layaMlx: { preset: 'triage' } },
    });

    expect(result.warnings).toEqual([
      { type: 'unsupported', feature: 'providerOptions.layaMlx.preset' },
    ]);
  });
});

describe('errors', () => {
  it('surfaces the FastAPI error detail', async () => {
    const { fetch } = stubFetch({
      status: 401,
      body: { detail: 'Missing or invalid API key' },
    });
    const model = createLayaMlx({ fetch }).evaluationModel('x');

    await expect(evaluate(model)).rejects.toThrow(/Missing or invalid API key/);
  });

  it('surfaces validation errors raised by the server', async () => {
    const { fetch } = stubFetch({
      status: 400,
      body: { detail: "Provide 'questions' or a 'preset'" },
    });
    const model = createLayaMlx({ fetch }).evaluationModel('x');

    await expect(evaluate(model)).rejects.toThrow(/questions/);
  });
});

describe('provider surface', () => {
  it('is a v4 provider with only an evaluation model factory', () => {
    const provider = createLayaMlx();
    expect(provider.specificationVersion).toBe('v4');
    expect(layaMlx.evaluationModel('laya-mlx').specificationVersion).toBe('v4');
    expect(layaMlx.evaluationModel('laya-mlx').supportedQuestionTypes).toEqual([
      'choice',
      'score',
      'boolean',
    ]);
    expect(() => provider.languageModel('anything')).toThrow(NoSuchModelError);
    expect(() => provider.embeddingModel('anything')).toThrow(NoSuchModelError);
    expect(() => provider.imageModel('anything')).toThrow(NoSuchModelError);
  });
});
