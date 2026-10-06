import {
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  signal,
  untracked,
  viewChild,
  DestroyRef,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideCheck } from '@ng-icons/lucide';
import { ConfirmsLeaving } from '@app/core/guards/leave-confirmation-guard';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import {
  exhaustMap,
  filter,
  finalize,
  firstValueFrom,
  Observable,
  Subscription,
  take,
  throwIfEmpty,
  timer,
} from 'rxjs';
import { ApiError, toApiError } from '@app/core/api/api-error';
import {
  DECLINE_ASK_BACK_MESSAGE,
  OPENING_MAX_POLLS,
  OPENING_POLL_INTERVAL_MS,
} from '@app/features/interviews/interviews.constants';
import { InterviewerVoice } from '@app/core/speech/interviewer-voice';
import { VoiceToggle } from '@app/features/interviews/components/voice-toggle/voice-toggle';
import { InterviewsApi } from '@app/features/interviews/services/interviews-api';
import { AbandonInterview } from './components/abandon-interview/abandon-interview';
import { AskBackSuggestions } from './components/ask-back-suggestions/ask-back-suggestions';
import { ChatComposer } from './components/chat-composer/chat-composer';
import { ChatTranscript } from './components/chat-transcript/chat-transcript';
import { InterviewerPanel } from './components/interviewer-panel/interviewer-panel';
import { Interview, Message } from '@app/features/interviews/models/interview.schema';

@Component({
  selector: 'app-interview-session',
  imports: [
    AbandonInterview,
    AskBackSuggestions,
    ChatComposer,
    ChatTranscript,
    HlmBadge,
    HlmButtonImports,
    HlmEmptyImports,
    HlmSkeleton,
    InterviewerPanel,
    NgIcon,
    VoiceToggle,
    RouterLink,
  ],
  providers: [provideIcons({ lucideCheck })],
  templateUrl: './interview-session.html',
  host: { '(window:beforeunload)': 'onBeforeUnload($event)' },
})
export class InterviewSession implements ConfirmsLeaving {
  readonly id = input.required<string>();

  private readonly api = inject(InterviewsApi);
  private readonly router = inject(Router);
  private readonly voice = inject(InterviewerVoice);
  /** Leaving on purpose (the abandon flow) needs no confirmation. */
  private readonly leavingOnPurpose = signal(false);
  private readonly interviewResource = rxResource({
    params: () => this.id(),
    stream: ({ params }) => this.api.get(params),
  });
  /** The loaded Interview, kept in step with every exchange without refetching it. */
  protected readonly interview = linkedSignal<Interview | undefined>(() =>
    this.interviewResource.hasValue() ? this.interviewResource.value() : undefined,
  );
  protected readonly loading = this.interviewResource.isLoading;
  protected readonly loadError = computed(() => {
    const error = this.interviewResource.error();
    return error ? toApiError(error) : null;
  });

  /** What belongs to the Interview on screen starts over when the route moves to another one. */
  protected readonly draft = linkedSignal<string, string>({
    source: this.id,
    computation: () => '',
  });
  protected readonly pendingReply = linkedSignal<string, string | null>({
    source: this.id,
    computation: () => null,
  });
  protected readonly sendError = linkedSignal<string, string | null>({
    source: this.id,
    computation: () => null,
  });
  /** The newest interviewer message is typed out; the ones loaded with the page are not. */
  protected readonly animatedMessageId = linkedSignal<string, string | null>({
    source: this.id,
    computation: () => null,
  });

  /** The interviewer's opening message is being fetched (or awaited from another request). */
  /** An earlier reply is still being answered (a reload mid-turn, or another tab): wait, don't resend. */
  protected readonly waitingForTurn = linkedSignal<string, boolean>({
    source: this.id,
    computation: () => false,
  });
  /** The newest interviewer message has been typed out (so the interview may be shown as over). */
  protected readonly lastMessageShown = linkedSignal<string | null, boolean>({
    source: this.animatedMessageId,
    computation: (id) => id === null,
  });
  protected readonly opening = linkedSignal<string, boolean>({
    source: this.id,
    computation: () => false,
  });
  protected readonly openingError = linkedSignal<string, string | null>({
    source: this.id,
    computation: () => null,
  });
  /** An Interview that was created but not opened yet has no messages, so nothing can be sent. */
  protected readonly awaitingOpening = computed(() => {
    const interview = this.interview();
    return !!interview && interview.status === 'in_progress' && interview.messages.length === 0;
  });
  protected readonly interviewerTyping = computed(
    () => this.sending() || this.opening() || this.waitingForTurn(),
  );
  /** Nothing can be sent while a reply, the opening or an earlier turn is being answered. */
  protected readonly replyBlocked = computed(
    () => this.sending() || this.awaitingOpening() || this.waitingForTurn(),
  );

  private readonly composer = viewChild(ChatComposer);
  private openingRequest: Subscription | null = null;
  private turnRequest: Subscription | null = null;
  /** Questions whose helper was asked for: once each, a failure is not retried. */
  private readonly helperRequested = new Set<string>();
  private readonly helperRequests = new Set<Subscription>();
  /** Questions whose helper is being written; their card shows a placeholder meanwhile. */
  protected readonly helperPending = linkedSignal<string, ReadonlySet<string>>({
    source: this.id,
    computation: () => new Set(),
  });
  private personaRequest: Subscription | null = null;
  /** Each is requested once per page load (the server is idempotent, but a model call is slow). */
  private openingRequestedFor: string | null = null;
  private portraitRequestedFor: string | null = null;
  /** The suggestion in the draft right now, until it is sent or the draft is cleared. */
  private readonly pendingSuggestion = linkedSignal<string, string | null>({
    source: this.id,
    computation: () => null,
  });
  protected readonly usedSuggestions = linkedSignal<string, readonly string[]>({
    source: this.id,
    computation: () => [],
  });
  protected readonly sending = computed(() => this.pendingReply() !== null);
  protected readonly ended = computed(() => this.interview()?.status !== 'in_progress');
  protected readonly personaImageUrl = computed(() =>
    this.interview()?.personaImageUrl ? this.api.personaImageUrl(this.id()) : null,
  );
  protected readonly questionsAsked = computed(
    () =>
      this.interview()?.messages.filter((m) => m.role === 'interviewer' && m.phase === 'qa')
        .length ?? 0,
  );
  protected readonly phaseLabel = computed(() =>
    this.interview()?.phase === 'ask_back' ? 'Ask-back phase' : 'Q&A phase',
  );
  /** The candidate's turn to ask the interviewer questions (or to decline). */
  protected readonly inAskBack = computed(
    () => this.interview()?.phase === 'ask_back' && !this.ended(),
  );
  /** Suggested questions are a coaching helper, and only make sense while the candidate is asking. */
  protected readonly suggestionsAvailable = computed(
    () => !!this.interview()?.coachingHelpersEnabled && this.inAskBack(),
  );
  protected readonly placeholder = computed(() =>
    this.interview()?.phase === 'ask_back'
      ? 'Ask the interviewer a question, or say you have none…'
      : 'Type your answer…',
  );

  constructor() {
    inject(DestroyRef).onDestroy(() => {
      this.cancelRequests();
      this.voice.cancel();
    });

    // The message being typed out is the one read aloud (when the voice is on); replying or
    // leaving silences it. Only the id is tracked, so nothing is read again when the Interview
    // changes in other ways.
    effect(() => {
      const id = this.animatedMessageId();
      untracked(() => {
        const message = id ? this.interview()?.messages.find((m) => m.id === id) : undefined;
        if (message) {
          this.voice.speak(message.content);
        } else {
          this.voice.cancel();
        }
      });
    });

    // Another Interview (route reuse): stop whatever was in flight for the previous one. Its state
    // starts over by itself (the linked signals above).
    effect(() => {
      this.id();
      untracked(() => {
        this.cancelRequests();
        this.helperRequested.clear();
        this.openingRequestedFor = null;
        this.portraitRequestedFor = null;
      });
    });

    // The server no longer opens the interview when it is created: ask for the opening message
    // and, in parallel, for the portrait, as soon as the Interview is loaded.
    effect(() => {
      const interview = this.interview();
      if (!interview) {
        return;
      }
      untracked(() => {
        if (this.awaitingOpening() && this.openingRequestedFor !== interview.id) {
          this.startOpening(interview.id);
        }
        // A finished interview needs no new (slow, paid) portrait.
        if (
          !interview.personaImageUrl &&
          interview.status === 'in_progress' &&
          this.portraitRequestedFor !== interview.id
        ) {
          this.startPortrait(interview.id);
        }
      });
    });

    // The question is shown at once and its coaching helper is asked for separately (it takes a
    // few seconds and never holds up answering). One rule covers the opening, every reply and a
    // page load: the newest message, if it is a Q&A question without a helper, gets one.
    effect(() => {
      const interview = this.interview();
      if (interview) {
        untracked(() => this.requestHelperFor(interview));
      }
    });
  }

  protected retryOpening(): void {
    this.startOpening(this.id());
  }

  private cancelRequests(): void {
    this.openingRequest?.unsubscribe();
    this.personaRequest?.unsubscribe();
    this.turnRequest?.unsubscribe();
    this.openingRequest = this.personaRequest = this.turnRequest = null;
    this.helperRequests.forEach((request) => request.unsubscribe());
    this.helperRequests.clear();
  }

  private requestHelperFor(interview: Interview): void {
    const last = interview.messages.at(-1);
    // Only the newest message, and only while it is still the open question: an older gap, or a
    // question the candidate already answered, gets no hint.
    if (
      !interview.coachingHelpersEnabled ||
      interview.status !== 'in_progress' ||
      last?.role !== 'interviewer' ||
      last.phase !== 'qa' ||
      last.helperText !== null ||
      this.helperRequested.has(last.id)
    ) {
      return;
    }
    this.helperRequested.add(last.id);
    this.setHelperPending(last.id, true);
    // Created first: the request can finish synchronously, and its cleanup needs this handle.
    const request = new Subscription();
    this.helperRequests.add(request);
    request.add(
      this.api
        .generateHelper(interview.id, last.id)
        .pipe(
          finalize(() => {
            this.setHelperPending(last.id, false);
            this.helperRequests.delete(request);
          }),
        )
        .subscribe({
          next: (message) => this.mergeHelper(interview.id, message),
          // The hint is a nicety: no banner, no retry, no card.
          error: () => undefined,
        }),
    );
  }

  /** Merged by message id, so a late answer for an older question lands on the right card. */
  private mergeHelper(interviewId: string, message: Message): void {
    if (message.helperText === null) {
      return;
    }
    this.interview.update((current) =>
      current?.id === interviewId
        ? {
            ...current,
            messages: current.messages.map((m) =>
              m.id === message.id ? { ...m, helperText: message.helperText } : m,
            ),
          }
        : current,
    );
  }

  private setHelperPending(messageId: string, pending: boolean): void {
    this.helperPending.update((ids) => {
      const next = new Set(ids);
      if (pending) {
        next.add(messageId);
      } else {
        next.delete(messageId);
      }
      return next;
    });
  }

  private startOpening(id: string): void {
    this.openingRequest?.unsubscribe();
    this.openingRequestedFor = id;
    this.openingError.set(null);
    this.opening.set(true);
    this.openingRequest = this.api.openInterview(id).subscribe({
      next: (message) => {
        this.opening.set(false);
        // Abandoned meanwhile: the ended state wins, the opening is not shown.
        if (this.interview()?.id === id && !this.ended() && this.awaitingOpening()) {
          this.interview.update((current) =>
            current ? { ...current, messages: [message] } : current,
          );
          this.animatedMessageId.set(message.id);
        }
      },
      error: (err: unknown) => this.onOpeningFailed(id, toApiError(err)),
    });
  }

  private onOpeningFailed(id: string, error: ApiError): void {
    if (error.code === 'INTERVIEW_ALREADY_ENDED') {
      this.opening.set(false);
      this.interviewResource.reload();
    } else if (error.code === 'TURN_IN_PROGRESS') {
      // Another request (a reload, a double mount) is opening it right now: wait for its result.
      this.openingRequest = this.waitForOpening(id).subscribe({
        next: (interview) => {
          this.opening.set(false);
          if (this.interview()?.id === id) {
            this.interview.set(interview);
            const first = interview.messages[0];
            if (interview.status === 'in_progress' && first?.role === 'interviewer') {
              this.animatedMessageId.set(first.id);
            }
          }
        },
        error: (err: unknown) => this.onOpeningFailed(id, toApiError(err)),
      });
    } else {
      this.opening.set(false);
      this.openingError.set(error.message);
    }
  }

  /** Re-reads the Interview until it has messages (or has ended); fails if that takes too long. */
  private waitForOpening(id: string): Observable<Interview> {
    return this.pollInterview(
      id,
      (interview) => interview.messages.length > 0 || interview.status !== 'in_progress',
      new ApiError('OPENING_TIMEOUT', 'The interviewer is taking too long to start.', 0),
    );
  }

  /** Re-reads the Interview until `isReady` says so; fails with `timeout` if that takes too long. */
  private pollInterview(
    id: string,
    isReady: (interview: Interview) => boolean,
    timeout: ApiError,
  ): Observable<Interview> {
    return timer(OPENING_POLL_INTERVAL_MS, OPENING_POLL_INTERVAL_MS).pipe(
      take(OPENING_MAX_POLLS),
      // A poll still waiting for its answer is not cancelled by the next tick: it would never finish.
      exhaustMap(() => this.api.get(id)),
      filter(isReady),
      take(1),
      throwIfEmpty(() => timeout),
    );
  }

  /**
   * The server refused a reply because the previous one is still being answered (`TURN_IN_PROGRESS`):
   * it must not be sent again. Wait for that turn to finish, then show what it produced.
   */
  private waitForTurnToFinish(id: string): void {
    const known = this.interview()?.messages.length ?? 0;
    this.waitingForTurn.set(true);
    this.turnRequest?.unsubscribe();
    this.turnRequest = this.pollInterview(
      id,
      (interview) => interview.messages.length > known || interview.status !== 'in_progress',
      new ApiError(
        'TURN_TIMEOUT',
        'The interviewer is taking too long to answer. Reload the page to see the latest messages.',
        0,
      ),
    ).subscribe({
      next: (interview) => {
        this.waitingForTurn.set(false);
        if (this.id() !== id) {
          return;
        }
        this.interview.set(interview);
        const last = interview.messages.at(-1);
        if (interview.status === 'in_progress' && last?.role === 'interviewer') {
          this.animatedMessageId.set(last.id);
        }
      },
      error: (err: unknown) => {
        this.waitingForTurn.set(false);
        this.sendError.set(toApiError(err).message);
      },
    });
  }

  /** The portrait is cosmetic: on failure or when switched off the fallback avatar stays. */
  private startPortrait(id: string): void {
    this.personaRequest?.unsubscribe();
    this.portraitRequestedFor = id;
    this.personaRequest = this.api.generatePersonaImage(id).subscribe({
      next: (url) => {
        if (url) {
          this.interview.update((current) =>
            current?.id === id ? { ...current, personaImageUrl: url } : current,
          );
        }
      },
      error: () => undefined,
    });
  }

  protected async onSend(content: string): Promise<void> {
    if (this.awaitingOpening()) {
      return;
    }
    // The reply belongs to this Interview: if the page moves on to another one while it is being
    // answered, nothing of the result may land on the new Interview.
    const interviewId = this.id();
    const moved = () => this.id() !== interviewId;
    const suggestion = this.pendingSuggestion();
    this.pendingSuggestion.set(null);
    this.sendError.set(null);
    this.animatedMessageId.set(null);
    this.pendingReply.set(content);
    this.draft.set('');
    try {
      const exchange = await firstValueFrom(this.api.sendMessage(interviewId, content));
      if (moved()) {
        return;
      }
      this.interview.update((current) =>
        current
          ? {
              ...current,
              phase: exchange.phase,
              status: exchange.status,
              messages: [
                ...current.messages,
                exchange.candidateMessage,
                exchange.interviewerMessage,
              ],
            }
          : current,
      );
      this.animatedMessageId.set(exchange.interviewerMessage.id);
      if (suggestion) {
        this.usedSuggestions.update((used) => [...used, suggestion]);
      }
    } catch (err) {
      if (moved()) {
        return;
      }
      const error = toApiError(err);
      if (error.code === 'INTERVIEW_ALREADY_ENDED') {
        // Abandoned (here or elsewhere) while the interviewer was answering: show the ended state.
        this.interviewResource.reload();
      } else {
        // An exchange is all-or-nothing: nothing was stored, so the reply goes back to be sent again.
        if (this.draft() === '') {
          this.draft.set(content);
          this.pendingSuggestion.set(suggestion);
        }
        if (error.code === 'TURN_IN_PROGRESS') {
          this.sendError.set(
            'The interviewer was still answering your previous reply, so this one was not sent. Your text is back in the box.',
          );
          this.waitForTurnToFinish(interviewId);
        } else {
          this.sendError.set(error.message);
        }
      }
    } finally {
      if (!moved()) {
        this.pendingReply.set(null);
      }
    }
  }

  /**
   * An emptied draft drops the pick: whatever is typed next is not that suggestion. Done here, as
   * it happens, because a derived value would only ever see the draft when read and could miss
   * the moment it was empty.
   */
  protected onDraftChange(draft: string): void {
    this.draft.set(draft);
    if (draft === '') {
      this.pendingSuggestion.set(null);
    }
  }

  /** Declining is a message like any other: the interviewer answers it and closes the interview. */
  protected declineQuestions(): void {
    // A suggestion that was picked but not sent is not what is being sent now.
    this.pendingSuggestion.set(null);
    void this.onSend(DECLINE_ASK_BACK_MESSAGE);
  }

  /** Suggestions said they are no longer possible: re-read the interview, which says why. */
  protected onSuggestionsUnavailable(): void {
    this.interviewResource.reload();
  }

  protected onSuggestionPicked(suggestion: string): void {
    this.draft.set(suggestion);
    this.pendingSuggestion.set(suggestion);
    this.composer()?.focus();
  }

  /** A running interview stays open when the page is left, so the candidate is asked first. */
  leaveConfirmation(): string | null {
    return this.interview()?.status === 'in_progress' && !this.leavingOnPurpose()
      ? 'This interview is still in progress. It stays open, but ends by itself after 30 minutes without activity. Leave anyway?'
      : null;
  }

  protected onBeforeUnload(event: BeforeUnloadEvent): void {
    if (this.leaveConfirmation() !== null) {
      event.preventDefault();
    }
  }

  protected async onAbandoned(): Promise<void> {
    this.leavingOnPurpose.set(true);
    const navigated = await this.router.navigate(['/interviews', this.id(), 'results']);
    if (!navigated) {
      this.leavingOnPurpose.set(false);
    }
  }
}
