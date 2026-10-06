import {
  disabled,
  maxLength,
  SchemaPath,
  SchemaPathTree,
  validateStandardSchema,
} from '@angular/forms/signals';
import { z } from 'zod';
import {
  difficultySchema,
  interviewerRoleSchema,
  interviewTypeSchema,
  responseStyleSchema,
  senioritySchema,
  toneSchema,
} from '@app/features/interviews/models/interview.enums';
import {
  COMPANY_NAME_MAX_LENGTH,
  JOB_TITLE_MAX_LENGTH,
  MAX_QUESTION_COUNT,
} from '@app/features/interviews/interviews.constants';
import { phaseSettingsOverrideSchema } from '@app/core/phase-settings/phase-settings.schema';

export const createInterviewSchema = z
  .object({
    applicationMode: z.enum(['standalone', 'existing', 'new']),
    applicationId: z.string().nullable(),
    jobTitle: z.string().trim().min(1, 'Enter a job title'),
    companyName: z.string().trim(),
    seniority: senioritySchema,
    difficulty: difficultySchema,
    targetQuestionCount: z
      .number({ error: 'Enter a number of questions' })
      .int('Use a whole number')
      .min(1, 'At least 1 question')
      .max(MAX_QUESTION_COUNT, `At most ${MAX_QUESTION_COUNT} questions`),
    tone: toneSchema,
    responseStyle: responseStyleSchema,
    interviewerRole: interviewerRoleSchema,
    interviewType: interviewTypeSchema,
    jobDescriptionId: z.string().nullable(),
    cvId: z.string().nullable(),
    coverLetterId: z.string().nullable(),
    coachingHelpersEnabled: z.boolean(),
    phaseSettings: phaseSettingsOverrideSchema,
  })
  .refine((form) => form.applicationMode !== 'existing' || form.applicationId, {
    path: ['applicationId'],
    error: 'Choose an application',
  });

/** Form state for Create Interview */
export type CreateInterviewModel = z.infer<typeof createInterviewSchema>;

/** Starting values for a blank form. */
export function initialCreateInterviewModel(): CreateInterviewModel {
  return {
    applicationMode: 'standalone',
    applicationId: null,
    jobTitle: '',
    companyName: '',
    seniority: 'mid',
    difficulty: 'medium',
    targetQuestionCount: 8,
    tone: 'neutral',
    responseStyle: 'concise',
    interviewerRole: 'recruiter',
    interviewType: 'behavioral',
    jobDescriptionId: null,
    cvId: null,
    coverLetterId: null,
    coachingHelpersEnabled: false,
    phaseSettings: {},
  };
}

export function createInterviewValidation(path: SchemaPathTree<CreateInterviewModel>): void {
  validateStandardSchema(path, createInterviewSchema);
  // These come from the chosen Application, so they can't be edited while one is selected.
  const lockedByApplication = <T>(field: SchemaPath<T>) =>
    disabled(
      field,
      ({ valueOf }) =>
        valueOf(path.applicationMode) === 'existing' && valueOf(path.applicationId) !== null,
    );
  lockedByApplication(path.jobTitle);
  lockedByApplication(path.companyName);
  lockedByApplication(path.seniority);
  lockedByApplication(path.jobDescriptionId);
  lockedByApplication(path.cvId);
  lockedByApplication(path.coverLetterId);
  // Declared on the form (not in the schema) so the input also gets the native `maxlength`.
  maxLength(path.jobTitle, JOB_TITLE_MAX_LENGTH, {
    message: `Keep it under ${JOB_TITLE_MAX_LENGTH} characters`,
  });
  maxLength(path.companyName, COMPANY_NAME_MAX_LENGTH, {
    message: `Keep it under ${COMPANY_NAME_MAX_LENGTH} characters`,
  });
}
