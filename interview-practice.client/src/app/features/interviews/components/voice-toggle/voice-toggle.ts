import { Component, inject } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideVolume2, lucideVolumeX } from '@ng-icons/lucide';
import { HlmToggleImports } from '@spartan-ng/helm/toggle';
import { HlmTooltipImports } from '@spartan-ng/helm/tooltip';
import { InterviewerVoice } from '@app/core/speech/interviewer-voice';

/** Switches the interviewer's voice on or off; the same setting wherever this is shown. */
@Component({
  selector: 'app-voice-toggle',
  imports: [HlmToggleImports, HlmTooltipImports, NgIcon],
  providers: [provideIcons({ lucideVolume2, lucideVolumeX })],
  templateUrl: './voice-toggle.html',
  host: { class: 'inline-flex' },
})
export class VoiceToggle {
  protected readonly voice = inject(InterviewerVoice);
}
