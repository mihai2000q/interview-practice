import { z } from 'zod';
import { ApiError } from '@app/core/api/api-error';

/** `details` of `422 INPUT_REJECTED` on `POST /api/interviews` (docs/api-design.md). */
const inputRejectedDetailsSchema = z.object({
  reason: z.enum(['prompt_injection', 'too_long', 'moderation']),
  field: z.string().optional(),
  excerpt: z.string().optional(),
  maxLength: z.number().optional(),
});

/** The form fields that carry free text and can be rejected. */
export type RejectableField = 'jobTitle' | 'companyName';

export interface InputRejection {
  message: string;
  /** The form field to show it on; none when the server named a field that has no input of its own. */
  field: RejectableField | null;
}

export function describeInputRejection(error: ApiError): InputRejection {
  const details = inputRejectedDetailsSchema.safeParse(error.details);
  if (!details.success) {
    return { message: error.message, field: null };
  }
  const { reason, field, excerpt, maxLength } = details.data;
  const message =
    reason === 'too_long' && maxLength !== undefined
      ? `Keep this under ${maxLength} characters.`
      : reason === 'prompt_injection' && excerpt
        ? `${error.message} It was triggered by: “${excerpt}”.`
        : error.message;
  return { message, field: field === 'jobTitle' || field === 'companyName' ? field : null };
}
