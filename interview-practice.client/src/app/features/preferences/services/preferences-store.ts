import { computed, inject, Service } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { toApiError } from '@app/core/api/api-error';
import { valueOrUndefined } from '@app/core/api/resource-value';
import { builtInModelOf, Phase } from '@app/features/interviews/models/phase-settings.schema';
import { PhasePreferences, Preferences } from '../models/preferences.schema';
import { PreferencesApi } from './preferences-api';

/** What a phase uses when nothing has been customized. */
export function builtInPreferences(phase: Phase): PhasePreferences {
  return {
    model: builtInModelOf(phase),
    temperature: null,
    maxTokens: null,
    reasoningEffort: null,
  };
}

/**
 * The saved Preferences, read once and shared: the Preferences page edits them, and Create
 * Interview shows them as the defaults an Interview starts from. Until they are loaded (or if
 * that failed) every phase reads as its built-in defaults, which is also what the server uses
 * when nothing was customized.
 */
@Service()
export class PreferencesStore {
  private readonly api = inject(PreferencesApi);
  private readonly preferencesResource = rxResource({ stream: () => this.api.get() });

  /** `undefined` while loading or after a failure to load. */
  readonly preferences = computed(() => valueOrUndefined(this.preferencesResource));
  readonly loadError = computed(() => {
    const error = this.preferencesResource.error();
    return error ? toApiError(error).message : null;
  });

  /** What `phase` runs on by default. */
  phase(phase: Phase): PhasePreferences {
    return this.preferences()?.[phase] ?? builtInPreferences(phase);
  }

  /** Takes what the server answered to a save as the new Preferences. */
  replace(preferences: Preferences): void {
    this.preferencesResource.set(preferences);
  }

  reload(): void {
    this.preferencesResource.reload();
  }
}
