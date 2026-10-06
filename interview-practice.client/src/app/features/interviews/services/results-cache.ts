import { inject, Service } from '@angular/core';
import { Observable, of, tap } from 'rxjs';
import { InterviewHistory } from '@app/features/history/interview-history';
import { Evaluation, InterviewerReview } from '../models/evaluation.schema';
import { Interview } from '../models/interview.schema';
import { InterviewsApi } from './interviews-api';

/**
 * What the Results page shows, kept for as long as the app is open. Once an Interview has ended
 * its transcript cannot change, and its Evaluation and InterviewerReview are never made again
 * (ADR 0014), so opening the same results a second time needs no request at all. Only a final
 * answer is kept: not an Interview still in progress, nor a missing review (it is `null` when
 * none was stored, which the server may still change its mind about until it has tried).
 */
@Service()
export class ResultsCache {
  private readonly api = inject(InterviewsApi);
  private readonly history = inject(InterviewHistory);

  private readonly evaluations = new Map<string, Evaluation>();
  private readonly interviews = new Map<string, Interview>();
  private readonly reviews = new Map<string, InterviewerReview>();

  /** What is kept for `id`, to show at once instead of waiting for a request to answer. */
  kept(id: string): { evaluation?: Evaluation; interview?: Interview; review?: InterviewerReview } {
    return {
      evaluation: this.evaluations.get(id),
      interview: this.interviews.get(id),
      review: this.reviews.get(id),
    };
  }

  /** Makes the Evaluation the first time, which is the slow call. */
  evaluation(id: string): Observable<Evaluation> {
    return this.cached(this.evaluations, id, () =>
      this.api.generateEvaluation(id).pipe(
        // The history lists the Interview without a verdict until its Evaluation exists.
        tap(() => this.history.refresh()),
      ),
    );
  }

  interview(id: string): Observable<Interview> {
    return this.cached(
      this.interviews,
      id,
      () => this.api.get(id),
      (interview) => interview.status !== 'in_progress',
    );
  }

  review(id: string): Observable<InterviewerReview | null> {
    return this.cached(
      this.reviews,
      id,
      () => this.api.getInterviewerReview(id),
      () => true,
    );
  }

  /** `isFinal` says whether an answer may be kept; `null` (no review) never is. */
  private cached<T extends object, R extends T | null = T>(
    cache: Map<string, T>,
    id: string,
    load: () => Observable<R>,
    isFinal: (value: T) => boolean = () => true,
  ): Observable<R> {
    const hit = cache.get(id);
    return hit
      ? of(hit as R)
      : load().pipe(
          tap((value) => {
            if (value && isFinal(value)) {
              cache.set(id, value);
            }
          }),
        );
  }
}
