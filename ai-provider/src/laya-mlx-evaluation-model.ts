import {
  InvalidArgumentError,
  type Experimental_EvaluationModelV4 as EvaluationModelV4,
  type Experimental_EvaluationModelV4Answer as EvaluationModelV4Answer,
  type Experimental_EvaluationModelV4CallOptions as EvaluationModelV4CallOptions,
  type Experimental_EvaluationModelV4Question as EvaluationModelV4Question,
  type Experimental_EvaluationModelV4Result as EvaluationModelV4Result,
  type SharedV4Warning,
} from '@ai-sdk/provider';
import {
  combineHeaders,
  createJsonResponseHandler,
  postJsonToApi,
  resolve,
  withUserAgentSuffix,
  type FetchFunction,
  type Resolvable,
} from '@ai-sdk/provider-utils';
import {
  layaEvaluationResponseSchema,
  layaFailedResponseHandler,
} from './laya-mlx-api.js';
import { VERSION } from './version.js';

export type LayaMlxEvaluationModelId = 'laya-mlx' | (string & {});

type LayaMlxEvaluationModelConfig = {
  provider: string;
  baseURL: string;
  headers: Resolvable<Record<string, string | undefined>>;
  fetch?: FetchFunction;
};

/** Layas server rounds probabilities and scores to four decimal places. */
const ROUNDING = { probabilityDecimals: 4, scoreDecimals: 4 } as const;

function toInstructions(value: unknown): string {
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function toCriterion(value: unknown, nullValue: string | null): string | null {
  if (value == null) return nullValue;
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function mapQuestion(question: EvaluationModelV4Question): unknown {
  switch (question.type) {
    case 'choice': {
      return {
        type: 'choice',
        instructions: toInstructions(question.instructions),
        criteria: Object.fromEntries(
          Object.entries(question.criteria).map(([option, description]) => [
            option,
            toCriterion(description, null),
          ]),
        ),
      };
    }
    case 'score': {
      return {
        type: 'score',
        instructions: toInstructions(question.instructions),
        // Laya renders a null level as "level N: null"; an empty string keeps it blank.
        criteria: question.criteria.map(level => toCriterion(level, '')),
      };
    }
    case 'boolean': {
      const criteria = question.criteria;
      return {
        // Laya's boolean primitive is called "noul".
        type: 'noul',
        instructions: toInstructions(question.instructions),
        ...(criteria === undefined
          ? {}
          : {
              criteria: Object.fromEntries(
                Object.entries(criteria).map(([outcome, description]) => [
                  outcome,
                  toCriterion(description, null),
                ]),
              ),
            }),
      };
    }
  }
}

function toStateText(state: EvaluationModelV4CallOptions['state']): string {
  return typeof state === 'string' ? state : JSON.stringify(state);
}

function mapAnswers(
  answers: Record<string, { type: string } & Record<string, unknown>>,
): Record<string, EvaluationModelV4Answer> {
  return Object.fromEntries(
    Object.entries(answers).map(([id, answer]): [string, EvaluationModelV4Answer] => {
      switch (answer.type) {
        case 'choice':
          return [
            id,
            {
              type: 'choice',
              choice: answer.choice as string,
              probabilities: answer.probabilities as Record<string, number>,
            },
          ];
        case 'score':
          return [
            id,
            {
              type: 'score',
              score: answer.score as number,
              probabilities: answer.probabilities as Record<string, number>,
            },
          ];
        case 'noul':
          return [id, { type: 'boolean', probability: answer.noul as number }];
        default:
          throw new InvalidArgumentError({
            argument: 'answers',
            message: `Unsupported answer type ${String(answer.type)}.`,
          });
      }
    }),
  );
}

export class EvaluationLayaMlxModel implements EvaluationModelV4 {
  readonly specificationVersion = 'v4' as const;
  readonly supportedQuestionTypes = ['choice', 'score', 'boolean'] as const;

  constructor(
    readonly modelId: LayaMlxEvaluationModelId,
    private readonly config: LayaMlxEvaluationModelConfig,
  ) {}

  get provider() {
    return this.config.provider;
  }

  async doEvaluate({
    state,
    questions,
    headers,
    abortSignal,
    providerOptions,
  }: EvaluationModelV4CallOptions): Promise<EvaluationModelV4Result> {
    for (const [id, question] of Object.entries(questions)) {
      if (
        question.type === 'choice' &&
        Object.keys(question.criteria).length > 255
      ) {
        throw new InvalidArgumentError({
          argument: `questions.${id}.criteria`,
          message: 'Laya choice questions support at most 255 options.',
        });
      }
    }

    const warnings: SharedV4Warning[] = Object.keys(
      providerOptions?.layaMlx ?? {},
    ).map(option => ({
      type: 'unsupported',
      feature: `providerOptions.layaMlx.${option}`,
    }));

    const {
      value: response,
      rawValue,
      responseHeaders,
    } = await postJsonToApi({
      url: `${this.config.baseURL}/v1/predict`,
      headers: combineHeaders(await resolve(this.config.headers), headers),
      body: {
        model: this.modelId,
        text: toStateText(state),
        questions: Object.fromEntries(
          Object.entries(questions).map(([id, question]) => [
            id,
            mapQuestion(question),
          ]),
        ),
      },
      abortSignal,
      fetch: this.config.fetch,
      failedResponseHandler: layaFailedResponseHandler,
      successfulResponseHandler: createJsonResponseHandler(
        layaEvaluationResponseSchema,
      ),
    });

    const confidence = Object.fromEntries(
      Object.entries(response.answers).flatMap(([id, answer]) =>
        answer.confidence != null ? [[id, answer.confidence]] : [],
      ),
    );

    return {
      answers: mapAnswers(response.answers),
      usage: {
        inputTokens: response.usage?.input_tokens ?? undefined,
        outputTokens: response.usage?.output_tokens ?? undefined,
      },
      rounding: ROUNDING,
      warnings,
      providerMetadata: { layaMlx: { confidence } },
      response: {
        modelId: response.model ?? this.modelId,
        headers: responseHeaders,
        body: rawValue,
      },
    };
  }
}
