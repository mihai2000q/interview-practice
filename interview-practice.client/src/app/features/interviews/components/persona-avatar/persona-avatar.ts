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
  /** `sm` is the chat avatar; `lg` is the rounded portrait used as a page header. */
  readonly size = input<'sm' | 'lg'>('sm');

  protected readonly avatarClass = computed(() =>
    this.size() === 'lg' ? 'size-16 rounded-xl after:rounded-xl' : '',
  );
  protected readonly imageClass = computed(() => (this.size() === 'lg' ? 'rounded-xl' : ''));
  protected readonly initialsClass = computed(() =>
    this.size() === 'lg' ? 'rounded-xl text-lg' : 'text-xs font-medium',
  );
  protected readonly imageSize = computed(() => (this.size() === 'lg' ? 64 : 32));

  protected readonly initials = computed(() => initialsOf(this.name()));
}
