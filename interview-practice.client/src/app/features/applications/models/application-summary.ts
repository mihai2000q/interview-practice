export type InterviewStatus = 'in_progress' | 'completed' | 'abandoned';

export interface ApplicationStage {
  id: string;
  interviewerRole: string;
  status: InterviewStatus;
}

/** A Document attached to an application, with its name so it can be shown without a lookup. */
export interface ApplicationDocument {
  id: string;
  name: string;
  /** The model that made its cached analysis; null while it has none. */
  analysisModel: string | null;
}

export interface ApplicationSummary {
  id: string;
  companyName: string | null;
  jobTitle: string;
  jobDescription: ApplicationDocument | null;
  cv: ApplicationDocument | null;
  coverLetter: ApplicationDocument | null;
  interviews: ApplicationStage[];
}
