import { DOCUMENT } from '@angular/common';
import { inject, Service, signal } from '@angular/core';
import { InterviewerVoice } from './interviewer-voice';
import { MicrophoneLevels } from './microphone-levels';

/** The parts of the Web Speech API's `SpeechRecognition` used here (TypeScript has no types for it). */
interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;
type WindowWithSpeech = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

const ERROR_MESSAGES: Record<string, string> = {
  'not-allowed': 'Microphone access is blocked. Allow it in your browser to dictate.',
  'service-not-allowed': 'Your browser does not allow speech recognition here.',
  'audio-capture': 'No microphone was found.',
  network: 'Speech recognition needs a network connection.',
};

/**
 * Dictation with the browser's `SpeechRecognition` (docs/architecture.md). Supported in Chrome and
 * Edge, partly in Safari, not in Firefox; the browser may send the audio to its own speech service.
 */
@Service()
export class SpeechDictation {
  private readonly window = inject(DOCUMENT).defaultView as WindowWithSpeech | null;
  private readonly Recognition =
    this.window?.SpeechRecognition ?? this.window?.webkitSpeechRecognition;
  private readonly voice = inject(InterviewerVoice);
  private readonly microphone = inject(MicrophoneLevels);
  private recognition: SpeechRecognitionLike | null = null;

  readonly supported = !!this.Recognition;
  readonly listening = signal(false);
  readonly error = signal<string | null>(null);
  /** The live level meter's bars; empty where there is none (the caller shows text instead). */
  readonly levels = this.microphone.bars;

  /** Starts listening. `onText` gets everything said since the start, interim words included. */
  start(onText: (text: string) => void): void {
    if (!this.Recognition || this.listening()) {
      return;
    }
    // The microphone would pick up the interviewer's voice.
    this.voice.cancel();
    this.error.set(null);
    const recognition = new this.Recognition();
    recognition.lang = this.window?.navigator.language || 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      const text = Array.from(event.results, (result) => result[0].transcript).join('');
      onText(text);
    };
    recognition.onerror = (event) => {
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        this.error.set(ERROR_MESSAGES[event.error] ?? 'Dictation stopped unexpectedly.');
      }
    };
    recognition.onend = () => {
      if (this.recognition === recognition) {
        this.recognition = null;
        this.listening.set(false);
        this.microphone.stop();
      }
    };
    this.recognition = recognition;
    this.listening.set(true);
    recognition.start();
    void this.microphone.start();
  }

  /** Stops listening and drops what was still being recognized (for when the text changed under it). */
  cancel(): void {
    const recognition = this.recognition;
    if (recognition) {
      this.recognition = null;
      this.listening.set(false);
      recognition.onresult = null;
      recognition.abort();
      this.microphone.stop();
    }
  }

  /** Stops listening but still delivers what was already heard. */
  stop(): void {
    this.recognition?.stop();
  }
}
