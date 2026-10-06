import { DOCUMENT } from '@angular/common';
import { inject, Service, signal } from '@angular/core';

const STORAGE_KEY = 'interview-practice.interviewer-voice';
/** Chrome stops reading a long utterance after about 15 s, so text is read in short pieces. */
const MAX_CHUNK_CHARS = 200;

/**
 * Reads the interviewer's messages aloud with the browser's `SpeechSynthesis` (docs/architecture.md).
 * Off by default; the choice is a browser preference, remembered here and not sent to the server.
 */
@Service()
export class InterviewerVoice {
  private readonly window = inject(DOCUMENT).defaultView;
  private readonly synth = this.window?.speechSynthesis;
  readonly supported = !!this.synth && typeof SpeechSynthesisUtterance !== 'undefined';
  readonly enabled = signal(this.supported && this.stored());

  setEnabled(enabled: boolean): void {
    this.enabled.set(enabled);
    this.store(enabled);
    if (!enabled) {
      this.cancel();
    }
  }

  /** Replaces whatever is being read with `text`; does nothing while the voice is off. */
  speak(text: string): void {
    if (!this.synth || !this.enabled()) {
      return;
    }
    this.synth.cancel();
    for (const chunk of chunksOf(text)) {
      const utterance = new SpeechSynthesisUtterance(chunk);
      utterance.lang = this.window?.navigator.language || 'en-US';
      this.synth.speak(utterance);
    }
  }

  cancel(): void {
    this.synth?.cancel();
  }

  private stored(): boolean {
    try {
      return this.window?.localStorage.getItem(STORAGE_KEY) === 'on';
    } catch {
      return false;
    }
  }

  private store(enabled: boolean): void {
    try {
      this.window?.localStorage.setItem(STORAGE_KEY, enabled ? 'on' : 'off');
    } catch {
      // Private mode or blocked storage: the choice just lasts until the page is closed.
    }
  }
}

/** Sentences, grouped into pieces of at most `MAX_CHUNK_CHARS` (a longer sentence is cut at words). */
export function chunksOf(text: string): string[] {
  const sentences = text.match(/[^.!?…]+[.!?…]*\s*/g) ?? [text];
  const chunks: string[] = [];
  let current = '';
  const flush = () => {
    if (current.trim()) {
      chunks.push(current.trim());
    }
    current = '';
  };
  for (const sentence of sentences) {
    if (current && current.length + sentence.length > MAX_CHUNK_CHARS) {
      flush();
    }
    if (sentence.length <= MAX_CHUNK_CHARS) {
      current += sentence;
      continue;
    }
    for (const word of sentence.split(/(?<=\s)/)) {
      if (current && current.length + word.length > MAX_CHUNK_CHARS) {
        flush();
      }
      current += word;
    }
  }
  flush();
  return chunks;
}
