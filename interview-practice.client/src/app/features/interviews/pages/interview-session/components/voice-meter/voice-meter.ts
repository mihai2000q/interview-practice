import { Component, input } from '@angular/core';

/** A row of bars, one per frequency band, sharing the width they are given (`flex-1`). */
@Component({
  selector: 'app-voice-meter',
  templateUrl: './voice-meter.html',
  host: { class: 'flex h-6 w-full items-center gap-0.5', 'aria-hidden': 'true' },
})
export class VoiceMeter {
  /** One value from 0 to 1 per bar. */
  readonly levels = input.required<readonly number[]>();
}
