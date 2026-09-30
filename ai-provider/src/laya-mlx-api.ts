import { createJsonErrorResponseHandler } from '@ai-sdk/provider-utils';
import * as z from 'zod/v4';

export const layaEvaluationResponseSchema = z.object({
  model: z.string().nullish(),
  answers: z.record(
    z.string(),
    z.discriminatedUnion('type', [
      z.object({
        type: z.literal('choice'),
        choice: z.string(),
        probabilities: z.record(z.string(), z.number()),
        confidence: z.number().nullish(),
      }),
      z.object({
        type: z.literal('score'),
        score: z.number(),
        probabilities: z.record(z.string(), z.number()),
        confidence: z.number().nullish(),
      }),
      z.object({
        type: z.literal('noul'),
        noul: z.number(),
        confidence: z.number().nullish(),
      }),
    ]),
  ),
  usage: z
    .object({
      input_tokens: z.number().nullish(),
      output_tokens: z.number().nullish(),
    })
    .nullish(),
});

export type LayEvaluationResponse = z.infer<typeof layaEvaluationResponseSchema>;

export const layaFailedResponseHandler = createJsonErrorResponseHandler({
  errorSchema: z.object({
    detail: z.unknown().nullish(),
    message: z.string().nullish(),
    error: z
      .union([z.string(), z.object({ message: z.string().nullish() })])
      .nullish(),
    error_type: z.string().nullish(),
  }),
  errorToMessage: error =>
    typeof error.detail === 'string'
      ? error.detail
      : error.detail != null
        ? JSON.stringify(error.detail)
        : error.message ??
          (typeof error.error === 'string'
            ? error.error
            : error.error?.message) ??
          error.error_type ??
          'Laya MLX request failed',
});
