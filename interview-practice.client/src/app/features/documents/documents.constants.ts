import type { DocumentType } from './models/document.schema';

/** Matches the server's default `MAX_UPLOAD_MB`, see docs/api-design.md. */
export const MAX_UPLOAD_MB = 10;

/** The kinds of Document, in the order they are listed. */
export const DOCUMENT_TYPES: readonly { value: DocumentType; plural: string; singular: string }[] =
  [
    { value: 'cv', plural: 'CVs', singular: 'CV' },
    { value: 'cover_letter', plural: 'Cover letters', singular: 'cover letter' },
    { value: 'job_description', plural: 'Job descriptions', singular: 'job description' },
  ];
