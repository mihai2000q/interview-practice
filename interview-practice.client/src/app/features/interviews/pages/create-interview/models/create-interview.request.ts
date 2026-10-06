import { CreateInterviewRequest } from '@app/features/interviews/models/create-interview.api';
import { CreateInterviewModel, createInterviewSchema } from './create-interview.schema';

function jobApplication(model: CreateInterviewModel): CreateInterviewRequest['jobApplication'] {
  switch (model.applicationMode) {
    case 'standalone':
      return null;
    case 'new':
      return { createNew: true };
    case 'existing':
      return model.applicationId ? { id: model.applicationId } : null;
  }
}

export function toCreateInterviewRequest(
  formModel: CreateInterviewModel,
): CreateInterviewRequest | null {
  const parsed = createInterviewSchema.safeParse(formModel);
  if (!parsed.success) {
    return null;
  }
  const model = parsed.data;
  return {
    jobTitle: model.jobTitle,
    companyName: model.companyName || undefined,
    seniority: model.seniority,
    difficulty: model.difficulty,
    targetQuestionCount: model.targetQuestionCount,
    tone: model.tone,
    interviewType: model.interviewType,
    interviewerRole: model.interviewerRole,
    responseStyle: model.responseStyle,
    coachingHelpersEnabled: model.coachingHelpersEnabled,
    jobDescriptionId: model.jobDescriptionId,
    cvId: model.cvId,
    coverLetterId: model.coverLetterId,
    jobApplication: jobApplication(model),
    phaseSettingsOverride:
      Object.keys(model.phaseSettings).length > 0 ? model.phaseSettings : undefined,
  };
}
