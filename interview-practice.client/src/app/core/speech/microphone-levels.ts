import { DOCUMENT } from '@angular/common';
import { inject, Service, signal } from '@angular/core';

/** How many bars the meter shows. */
const BAR_COUNT = 96;
/** Speech sits below about 4.5 kHz; with a 2048-point FFT at 48 kHz that is the first ~190 bins. */
const FFT_SIZE = 2048;
/** The lowest bins are rumble and DC offset, not voice (about 90 Hz and under). */
const FIRST_BIN = 4;
const BINS_PER_BAR = 2;
/** The meter is redrawn every other animation frame (about 30 per second). */
const FRAME_STRIDE = 2;

type WindowWithAudio = Window & {
  AudioContext?: typeof AudioContext;
  webkitAudioContext?: typeof AudioContext;
};

/**
 * The microphone's frequency bands as bar heights (0 to 1), read with the Web Audio API while
 * dictating, for a live level meter. Best effort: where it can't run (phones, which usually can't
 * share the microphone with speech recognition; reduced motion; no permission) `bars` stays empty
 * and the caller falls back to plain text.
 */
@Service()
export class MicrophoneLevels {
  private readonly window = inject(DOCUMENT).defaultView as WindowWithAudio | null;
  private run = 0;
  private cleanup: (() => void) | null = null;

  readonly bars = signal<readonly number[]>([]);

  async start(): Promise<void> {
    const window = this.window;
    const AudioContextType = window?.AudioContext ?? window?.webkitAudioContext;
    const getUserMedia = window?.navigator.mediaDevices?.getUserMedia?.bind(
      window.navigator.mediaDevices,
    );
    if (!window || !AudioContextType || !getUserMedia || this.unsuitable(window)) {
      return;
    }
    this.stop();
    const run = ++this.run;
    let stream: MediaStream;
    try {
      stream = await getUserMedia({ audio: true });
    } catch {
      return;
    }
    if (run !== this.run) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    const context = new AudioContextType();
    void context.resume();
    const analyser = context.createAnalyser();
    analyser.fftSize = FFT_SIZE;
    analyser.smoothingTimeConstant = 0.7;
    context.createMediaStreamSource(stream).connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);

    let frame = 0;
    let tick = 0;
    const draw = () => {
      frame = window.requestAnimationFrame(draw);
      if (tick++ % FRAME_STRIDE !== 0) {
        return;
      }
      analyser.getByteFrequencyData(data);
      const bars: number[] = [];
      for (let i = 0; i < BAR_COUNT; i++) {
        let sum = 0;
        for (let j = 0; j < BINS_PER_BAR; j++) {
          sum += data[FIRST_BIN + i * BINS_PER_BAR + j] ?? 0;
        }
        // A curve so quiet speech still moves the bars and loud speech doesn't pin them.
        bars.push(Math.pow(sum / BINS_PER_BAR / 255, 1.4));
      }
      this.bars.set(bars);
    };
    frame = window.requestAnimationFrame(draw);

    this.cleanup = () => {
      window.cancelAnimationFrame(frame);
      stream.getTracks().forEach((track) => track.stop());
      void context.close();
    };
  }

  stop(): void {
    this.run++;
    this.cleanup?.();
    this.cleanup = null;
    this.bars.set([]);
  }

  private unsuitable(window: Window): boolean {
    const phone = /Android|iPhone|iPad|iPod/i.test(window.navigator.userAgent);
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    return phone || reducedMotion;
  }
}
