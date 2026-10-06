import { HttpClient } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { z } from 'zod';
import { catchError, map, Observable, of, throwError } from 'rxjs';
import { environment } from '@env/environment';
import { mapApiError, toApiError } from '@app/core/api/api-error';
import { CreateInterviewRequest } from '../models/create-interview.api';
import {
  CreateInterviewResponse,
  createInterviewResponseSchema,
} from '../models/create-interview.api';
import { InterviewSummary, interviewSummarySchema } from '../models/interview-summary.schema';
import {
  Evaluation,
  evaluationSchema,
  InterviewerReview,
  interviewerReviewSchema,
} from '../models/evaluation.schema';
import {
  askBackSuggestionsSchema,
  Interview,
  interviewSchema,
  Message,
  MessageExchange,
  messageExchangeSchema,
  messageSchema,
  personaImageResultSchema,
} from '../models/interview.schema';

@Service()
export class InterviewsApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/interviews`;

  create(request: CreateInterviewRequest): Observable<CreateInterviewResponse> {
    return this.http.post<unknown>(this.url, request).pipe(
      map((body) => createInterviewResponseSchema.parse(body)),
      mapApiError(),
    );
  }

  /** Every Interview, newest first, without its messages: the history list. */
  list(): Observable<InterviewSummary[]> {
    return this.http.get<unknown>(this.url).pipe(
      map((body) => z.array(interviewSummarySchema).parse(body)),
      mapApiError(),
    );
  }

  get(id: string): Observable<Interview> {
    return this.http.get<unknown>(`${this.url}/${id}`).pipe(
      map((body) => interviewSchema.parse(body)),
      mapApiError(),
    );
  }

  /** The portrait is served by the API; the URL the API returns is relative to its own origin. */
  personaImageUrl(id: string): string {
    return `${this.url}/${id}/persona-image`;
  }

  /**
   * Asks the interviewer for the opening message of an Interview that has none yet. Idempotent:
   * once there are messages, the first one is returned without calling the model again.
   */
  openInterview(id: string): Observable<Message> {
    return this.http.put<unknown>(`${this.url}/${id}/opening`, null).pipe(
      map((body) => messageSchema.parse(body)),
      mapApiError(),
    );
  }

  /** Generates the portrait if there is none yet (idempotent); `null` when portraits are off. */
  generatePersonaImage(id: string): Observable<string | null> {
    return this.http.put<unknown>(`${this.url}/${id}/persona-image`, null).pipe(
      map((body) => personaImageResultSchema.parse(body).personaImageUrl),
      mapApiError(),
    );
  }

  sendMessage(id: string, content: string): Observable<MessageExchange> {
    return this.http.post<unknown>(`${this.url}/${id}/messages`, { content }).pipe(
      map((body) => messageExchangeSchema.parse(body)),
      mapApiError(),
    );
  }

  /**
   * Writes the coaching helper for an interviewer's Q&A question (idempotent, takes a few seconds).
   * A hint the model couldn't write comes back as `helperText: null`, not as an error.
   */
  generateHelper(id: string, messageId: string): Observable<Message> {
    return this.http.put<unknown>(`${this.url}/${id}/messages/${messageId}/helper`, null).pipe(
      map((body) => messageSchema.parse(body)),
      mapApiError(),
    );
  }

  abandon(id: string): Observable<Interview> {
    return this.http.post<unknown>(`${this.url}/${id}/abandon`, null).pipe(
      map((body) => interviewSchema.parse(body)),
      mapApiError(),
    );
  }

  /**
   * Makes the Evaluation of an ended Interview, and its InterviewerReview alongside it, from the
   * transcript. Idempotent: once they exist the stored Evaluation comes back without a model call.
   * A reasoning-model call, so it takes a while the first time.
   */
  generateEvaluation(id: string): Observable<Evaluation> {
    return this.http.put<unknown>(`${this.url}/${id}/evaluation`, null).pipe(
      map((body) => evaluationSchema.parse(body)),
      mapApiError(),
    );
  }

  /** `null` when there is no review: the judge's call failed, so none was stored. */
  getInterviewerReview(id: string): Observable<InterviewerReview | null> {
    return this.http.get<unknown>(`${this.url}/${id}/interviewer-review`).pipe(
      map((body) => interviewerReviewSchema.parse(body)),
      mapApiError(),
      catchError((err: unknown) =>
        toApiError(err).status === 404 ? of(null) : throwError(() => err),
      ),
    );
  }

  /** Ephemeral: the server makes up new questions on every call and stores none of them. */
  getAskBackSuggestions(id: string): Observable<string[]> {
    return this.http.get<unknown>(`${this.url}/${id}/ask-back-suggestions`).pipe(
      map((body) => askBackSuggestionsSchema.parse(body).suggestions),
      mapApiError(),
    );
  }
}
