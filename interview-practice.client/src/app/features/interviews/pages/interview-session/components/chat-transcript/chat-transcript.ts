import { Component, computed, input, linkedSignal, output } from '@angular/core';
import { HlmBubbleImports } from '@spartan-ng/helm/bubble';
import { HlmMarkerImports } from '@spartan-ng/helm/marker';
import { HlmMessageImports } from '@spartan-ng/helm/message';
import { HlmMessageScrollerImports } from '@spartan-ng/helm/message-scroller';
import { TypingIndicator } from '@app/shared/components/typing-indicator/typing-indicator';
import { InterviewStatus } from '@app/features/interviews/models/interview.enums';
import { Message } from '@app/features/interviews/models/interview.schema';
import { ChatMessage } from '../chat-message/chat-message';
import { PersonaAvatar } from '../persona-avatar/persona-avatar';

@Component({
  selector: 'app-chat-transcript',
  imports: [
    ChatMessage,
    HlmBubbleImports,
    HlmMarkerImports,
    HlmMessageImports,
    HlmMessageScrollerImports,
    PersonaAvatar,
    TypingIndicator,
  ],
  templateUrl: './chat-transcript.html',
  host: { class: 'flex min-h-0 flex-1 flex-col' },
})
export class ChatTranscript {
  readonly messages = input.required<readonly Message[]>();
  readonly personaName = input.required<string>();
  readonly personaImageUrl = input<string | null>(null);
  /** A candidate reply that was sent but not stored yet. */
  readonly pendingReply = input<string | null>(null);
  /** The interviewer is working on an answer. */
  readonly interviewerTyping = input(false);
  readonly status = input.required<InterviewStatus>();
  /** The message being typed out has been shown in full. */
  readonly typed = output();
  /** The interviewer message to type out; every other message shows in full. */
  readonly animatedMessageId = input<string | null>(null);
  /** Questions whose coaching helper is still being written. */
  readonly helperPendingIds = input<ReadonlySet<string>>(new Set());

  /** Interviewer messages the candidate has replied to, or is replying to right now. */
  protected readonly answeredIds = computed(() => {
    const messages = this.messages();
    const ids = new Set<string>();
    messages.forEach((message, i) => {
      if (message.role === 'candidate' && i > 0) {
        ids.add(messages[i - 1].id);
      }
    });
    if (this.pendingReply() !== null && messages.length > 0) {
      ids.add(messages[messages.length - 1].id);
    }
    return ids;
  });

  /** The message that opens the ask-back phase, where a divider goes. */
  protected readonly askBackStartId = computed(() => {
    const messages = this.messages();
    const index = messages.findIndex((m) => m.phase === 'ask_back');
    return index > 0 ? messages[index].id : null;
  });

  /** The last interviewer message is typed out before the interview is shown as over. */
  protected onTyped(): void {
    this.typingDone.set(true);
    this.typed.emit();
  }

  protected readonly typingDone = linkedSignal<string | null, boolean>({
    source: this.animatedMessageId,
    computation: (id) => id === null,
  });
  protected readonly endLabel = computed(() => {
    if (!this.typingDone()) {
      return null;
    }
    switch (this.status()) {
      case 'completed':
        return 'Interview completed';
      case 'abandoned':
        return 'Interview abandoned';
      default:
        return null;
    }
  });
}
