import { Component, DestroyRef, effect, inject, signal, untracked, viewChild } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideCheck } from '@ng-icons/lucide';
import { ConfirmsLeaving } from '@app/core/guards/leave-confirmation-guard';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { InterviewerVoice } from '@app/core/speech/interviewer-voice';
import { ChatTranscript } from '@app/features/interviews/components/chat-transcript/chat-transcript';
import { VoiceToggle } from '@app/features/interviews/components/voice-toggle/voice-toggle';
import { AbandonInterview } from './components/abandon-interview/abandon-interview';
import { AskBackSuggestions } from './components/ask-back-suggestions/ask-back-suggestions';
import { ChatComposer } from './components/chat-composer/chat-composer';
import { InterviewerPanel } from './components/interviewer-panel/interviewer-panel';
import { InterviewSessionStore } from './interview-session-store';

/** The live interview: what is on screen comes from the store, this page adds the browser side. */
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
  providers: [InterviewSessionStore, provideIcons({ lucideCheck })],
  templateUrl: './interview-session.html',
  host: { '(window:beforeunload)': 'onBeforeUnload($event)' },
})
export class InterviewSession implements ConfirmsLeaving {
  protected readonly store = inject(InterviewSessionStore);
  private readonly router = inject(Router);
  private readonly voice = inject(InterviewerVoice);
  /** Leaving on purpose (the abandon flow) needs no confirmation. */
  private readonly leavingOnPurpose = signal(false);
  private readonly composer = viewChild(ChatComposer);

  constructor() {
    inject(DestroyRef).onDestroy(() => this.voice.cancel());

    // The message being typed out is the one read aloud (when the voice is on); replying or
    // leaving silences it. Only the id is tracked, so nothing is read again when the Interview
    // changes in other ways.
    effect(() => {
      const id = this.store.animatedMessageId();
      untracked(() => {
        const message = id ? this.store.interview()?.messages.find((m) => m.id === id) : undefined;
        if (message) {
          this.voice.speak(message.content);
        } else {
          this.voice.cancel();
        }
      });
    });
  }

  protected onSuggestionPicked(suggestion: string): void {
    this.store.pickSuggestion(suggestion);
    this.composer()?.focus();
  }

  /** A running interview stays open when the page is left, so the candidate is asked first. */
  leaveConfirmation(): string | null {
    return this.store.interview()?.status === 'in_progress' && !this.leavingOnPurpose()
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
    const navigated = await this.router.navigate(['/interviews', this.store.id(), 'results']);
    if (!navigated) {
      this.leavingOnPurpose.set(false);
    }
  }
}
