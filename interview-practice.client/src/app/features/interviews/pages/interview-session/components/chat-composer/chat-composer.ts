import {
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  input,
  model,
  output,
  viewChild,
} from '@angular/core';
import { form, FormField, maxLength } from '@angular/forms/signals';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideMic, lucideSendHorizontal, lucideSquare } from '@ng-icons/lucide';
import { HlmInputGroupImports } from '@spartan-ng/helm/input-group';
import { HlmTooltipImports } from '@spartan-ng/helm/tooltip';
import { SpeechDictation } from '@app/core/speech/speech-dictation';
import { VoiceMeter } from '../voice-meter/voice-meter';
import { MAX_MESSAGE_LENGTH } from '@app/features/interviews/interviews.constants';

@Component({
  selector: 'app-chat-composer',
  imports: [FormField, HlmInputGroupImports, HlmTooltipImports, NgIcon, VoiceMeter],
  providers: [provideIcons({ lucideMic, lucideSendHorizontal, lucideSquare })],
  templateUrl: './chat-composer.html',
})
export class ChatComposer {
  readonly draft = model('');
  readonly placeholder = input('Type your answer…');
  /** A reply is being answered; the next one has to wait (the server refuses overlapping ones). */
  readonly busy = input(false);
  readonly send = output<string>();

  protected readonly dictation = inject(SpeechDictation);
  private readonly textarea = viewChild.required<ElementRef<HTMLTextAreaElement>>('reply');
  protected readonly maxLength = MAX_MESSAGE_LENGTH;
  /** Declared on the form so the textarea also gets the native `maxlength`. */
  protected readonly replyForm = form(this.draft, (path) => maxLength(path, MAX_MESSAGE_LENGTH));
  protected readonly trimmed = computed(() => this.draft().trim());
  protected readonly canSend = computed(() => !this.busy() && this.trimmed().length > 0);
  /**
   * With nothing to send, the send button would only sit disabled: where dictation works, the
   * microphone takes its place. It stays while listening, so the candidate can stop it.
   */
  protected readonly showMic = computed(
    () => this.dictation.supported && (this.trimmed().length === 0 || this.dictation.listening()),
  );
  protected readonly nearLimit = computed(() => this.draft().length > this.maxLength * 0.9);

  constructor() {
    inject(DestroyRef).onDestroy(() => this.dictation.cancel());
  }

  focus(): void {
    this.textarea().nativeElement.focus();
  }

  protected submit(): void {
    if (this.canSend()) {
      // A late result must not put the words back in the box after it was cleared.
      this.dictation.cancel();
      this.send.emit(this.trimmed());
    }
  }

  protected toggleDictation(): void {
    if (this.dictation.listening()) {
      this.dictation.stop();
      return;
    }
    const current = this.draft();
    const prefix = current && !/\s$/.test(current) ? `${current} ` : current;
    this.dictation.start((text) =>
      this.draft.set((prefix + text.trimStart()).slice(0, MAX_MESSAGE_LENGTH)),
    );
  }

  /** Typing takes over from dictation. */
  protected onTyped(): void {
    this.dictation.cancel();
  }

  /** Enter sends, Shift+Enter adds a line. Leaves IME composition alone. */
  protected onEnter(event: Event): void {
    const key = event as KeyboardEvent;
    if (key.shiftKey || key.isComposing) {
      return;
    }
    key.preventDefault();
    this.submit();
  }
}
