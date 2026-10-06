import { NgOptimizedImage } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import { HlmAvatarImports } from '@spartan-ng/helm/avatar';
import { initialsOf } from '@app/features/interviews/utils/initials';

/** The interviewer's portrait, or their initials while there is none (or it fails to load). */
@Component({
  selector: 'app-persona-avatar',
  imports: [HlmAvatarImports, NgOptimizedImage],
  templateUrl: './persona-avatar.html',
  host: { class: 'flex' },
})
export class PersonaAvatar {
  readonly name = input.required<string>();
  readonly imageUrl = input<string | null>(null);

  protected readonly initials = computed(() => initialsOf(this.name()));
}
