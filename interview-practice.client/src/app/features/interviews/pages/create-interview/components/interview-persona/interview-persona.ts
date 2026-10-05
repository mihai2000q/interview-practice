import { Component, input } from '@angular/core';
import { HlmCard, HlmCardContent, HlmCardHeader, HlmCardTitle } from '@spartan-ng/helm/card';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideLightbulb, lucideUserCog } from '@ng-icons/lucide';
import { FieldTree, FormField } from '@angular/forms/signals';
import { CreateInterviewModel } from '@app/features/interviews/pages/create-interview/models/create-interview.schema';
import { HlmField, HlmFieldGroup, HlmFieldLabel } from '@spartan-ng/helm/field';
import { HlmToggleGroup, HlmToggleGroupItem } from '@spartan-ng/helm/toggle-group';
import {
  INTERVIEWER_ROLES,
  INTERVIEWER_TONES,
  labelOf,
  ROLE_DEFAULTS,
} from '@app/features/interviews/pages/create-interview/models/create-interview.options';
import { HlmSelectImports } from '@spartan-ng/helm/select';
import { HlmAvatarImports } from '@spartan-ng/helm/avatar';
import { HlmSwitchImports } from '@spartan-ng/helm/switch';
import { VoiceToggle } from '@app/features/interviews/components/voice-toggle/voice-toggle';

@Component({
  providers: [provideIcons({ lucideUserCog, lucideLightbulb })],
  imports: [
    FormField,
    HlmCard,
    HlmCardContent,
    HlmCardHeader,
    HlmCardTitle,
    NgIcon,
    HlmField,
    HlmFieldLabel,
    HlmToggleGroup,
    HlmToggleGroupItem,
    HlmSelectImports,
    HlmFieldGroup,
    HlmAvatarImports,
    HlmSwitchImports,
    VoiceToggle,
  ],
  selector: 'app-interview-persona',
  templateUrl: './interview-persona.html',
})
export class InterviewPersona {
  readonly interviewForm = input.required<FieldTree<CreateInterviewModel>>();
  protected readonly interviewerRoles = INTERVIEWER_ROLES;
  protected readonly interviewerTones = INTERVIEWER_TONES;
  protected readonly interviewerRoleLabel = labelOf(INTERVIEWER_ROLES);

  /** Picking a role seeds the interview type and tone; both stay editable. */
  protected onRoleChange(role: unknown): void {
    if (typeof role !== 'string' || !(role in ROLE_DEFAULTS)) {
      return;
    }
    const defaults = ROLE_DEFAULTS[role as keyof typeof ROLE_DEFAULTS];
    const form = this.interviewForm();
    form.interviewType().value.set(defaults.interviewType);
    form.interviewType().markAsDirty();
    form.tone().value.set(defaults.tone);
    form.tone().markAsDirty();
  }
}
