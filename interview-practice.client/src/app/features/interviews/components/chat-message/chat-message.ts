import { Component, computed, input, output, signal } from '@angular/core';
import { MessageRole } from '@app/features/interviews/models/interview.enums';
import { HlmBubbleImports } from '@spartan-ng/helm/bubble';
import { HlmMessageImports } from '@spartan-ng/helm/message';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { Typewriter } from '@app/shared/components/typewriter/typewriter';
import { HintCard } from '../hint-card/hint-card';
import { PersonaAvatar } from '../persona-avatar/persona-avatar';

@Component({
  selector: 'app-chat-message',
  imports: [HintCard, HlmBubbleImports, HlmMessageImports, HlmSkeleton, PersonaAvatar, Typewriter],
  templateUrl: './chat-message.html',
})
export class ChatMessage {
  readonly role = input.required<MessageRole>();
  readonly content = input.required<string>();
  readonly helperText = input<string | null>(null);
  /** The helper is being written: a placeholder holds its place until it arrives. */
  readonly helperLoading = input(false);
  /** The candidate has replied to this question. */
  readonly answered = input(false);
  readonly personaName = input('');
  readonly personaImageUrl = input<string | null>(null);
  /** Type the interviewer's message out instead of showing it at once. */
  readonly animate = input(false);

  /** The interviewer's message has been shown in full. */
  readonly typed = output();

  private readonly typingDone = signal(false);
  protected readonly fromCandidate = computed(() => this.role() === 'candidate');
  /** The hint is held back until the question has been typed out. */
  protected readonly hintVisible = computed(() => !this.animate() || this.typingDone());

  protected onTyped(): void {
    this.typingDone.set(true);
    this.typed.emit();
  }
}
