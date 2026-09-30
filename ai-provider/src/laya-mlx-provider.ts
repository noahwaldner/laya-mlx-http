import {
  NoSuchModelError,
  type Experimental_EvaluationModelV4 as EvaluationModelV4,
  type ProviderV4,
} from '@ai-sdk/provider';
import {
  loadOptionalSetting,
  withoutTrailingSlash,
  withUserAgentSuffix,
  type FetchFunction,
} from '@ai-sdk/provider-utils';
import {
  EvaluationLayaMlxModel,
  type LayaMlxEvaluationModelId,
} from './laya-mlx-evaluation-model.js';
import { VERSION } from './version.js';

/** Layas evaluation capability, isolated from ProviderV4. */
export interface LayaMlxProvider extends ProviderV4 {
  evaluationModel(modelId: LayaMlxEvaluationModelId): EvaluationModelV4;
}

export interface LayaMlxProviderSettings {
  /** API key sent as X-API-Key. Optional: defaults to the LAYA_MLX_API_KEY environment variable. */
  apiKey?: string;
  /** Server base URL. Defaults to LAYA_MLX_BASE_URL or http://127.0.0.1:8000. */
  baseURL?: string;
  headers?: Record<string, string>;
  fetch?: FetchFunction;
}

export function createLayaMlx(
  options: LayaMlxProviderSettings = {},
): LayaMlxProvider {
  const baseURL =
    withoutTrailingSlash(
      options.baseURL ??
        loadOptionalSetting({
          settingValue: undefined,
          environmentVariableName: 'LAYA_MLX_BASE_URL',
        }) ??
        'http://127.0.0.1:8000',
    ) ?? 'http://127.0.0.1:8000';
  const apiKey =
    options.apiKey ??
    loadOptionalSetting({
      settingValue: undefined,
      environmentVariableName: 'LAYA_MLX_API_KEY',
    });
  const headers = () =>
    withUserAgentSuffix(
      {
        ...(apiKey === undefined ? {} : { 'X-API-Key': apiKey }),
        ...options.headers,
      },
      `ai-sdk-laya-mlx/${VERSION}`,
    );

  return {
    specificationVersion: 'v4',
    evaluationModel: modelId =>
      new EvaluationLayaMlxModel(modelId, {
        provider: 'laya-mlx.evaluation',
        baseURL,
        headers,
        fetch: options.fetch,
      }),
    languageModel: modelId => {
      throw new NoSuchModelError({ modelId, modelType: 'languageModel' });
    },
    embeddingModel: modelId => {
      throw new NoSuchModelError({ modelId, modelType: 'embeddingModel' });
    },
    imageModel: modelId => {
      throw new NoSuchModelError({ modelId, modelType: 'imageModel' });
    },
  };
}

export const layaMlx = createLayaMlx();
