import { HttpErrorResponse } from '@angular/common/http';
import { catchError, type MonoTypeOperatorFunction, throwError, TimeoutError } from 'rxjs';
import { z } from 'zod';

const errorBodySchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()).optional(),
  }),
});

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) {
    return err;
  }
  if (err instanceof HttpErrorResponse) {
    const body = errorBodySchema.safeParse(err.error);
    if (body.success) {
      const { code, message, details } = body.data.error;
      return new ApiError(code, message, err.status, details);
    }
    if (err.status === 0) {
      return new ApiError(
        'NETWORK_ERROR',
        'Could not reach the server. Check your connection and try again.',
        0,
      );
    }
  }
  if (err instanceof TimeoutError) {
    return new ApiError('TIMEOUT', 'The server took too long to answer. Please try again.', 0);
  }
  if (err instanceof z.ZodError) {
    return new ApiError('INVALID_RESPONSE', 'The server sent an unexpected response.', 0);
  }
  return new ApiError('UNKNOWN_ERROR', 'Something went wrong. Please try again.', 0);
}

/** Normalizes anything thrown in an HTTP pipeline into an `ApiError`. */
export function mapApiError<T>(): MonoTypeOperatorFunction<T> {
  return catchError((err: unknown) => throwError(() => toApiError(err)));
}
