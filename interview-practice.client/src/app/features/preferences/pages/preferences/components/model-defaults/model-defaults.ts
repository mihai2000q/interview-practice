import { Component, computed, inject, linkedSignal, signal } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideInfo, lucideRotateCcw } from '@ng-icons/lucide';
import { toast } from '@spartan-ng/brain/sonner';
import { HlmBadgeImports } from '@spartan-ng/helm/badge';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';
import { HlmFieldImports } from '@spartan-ng/helm/field';
import { HlmLabelImports } from '@spartan-ng/helm/label';
import { HlmSelectImports } from '@spartan-ng/helm/select';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { HlmSlider } from '@spartan-ng/helm/slider';
import { HlmSpinnerImports } from '@spartan-ng/helm/spinner';
import { HlmTooltipImports } from '@spartan-ng/helm/tooltip';
import { firstValueFrom } from 'rxjs';
import { toApiError } from '@app/core/api/api-error';
import {
  collidingPhases,
  isInterviewerPhase,
  isModelTaken,
  JudgeRuleModels,
  resolveRuleModels,
  takenNote,
} from '@app/features/interviews/models/judge-rule';
import {
  DEFAULT_JUDGE_MODEL,
  DEFAULT_MAX_TOKENS,
  DEFAULT_TEMPERATURE,
  INTERVIEW_MODELS,
  isSubStep,
  JUDGE_MODELS,
  MAX_TOKENS_RANGE,
  Phase,
  PHASE_HINTS,
  PHASE_LABELS,
  PHASE_STEPS,
  PHASES,
  REASONING_EFFORTS,
  TEMPERATURE_RANGE,
} from '@app/features/interviews/models/phase-settings.schema';
import {
  PhasePreferences,
  Preferences,
  PreferencesPatch,
} from '@app/features/preferences/models/preferences.schema';
import { PreferencesApi } from '@app/features/preferences/services/preferences-api';
import {
  builtInPreferences,
  PreferencesStore,
} from '@app/features/preferences/services/preferences-store';

function isBuiltIn(phase: Phase, preferences: PhasePreferences): boolean {
  const builtIn = builtInPreferences(phase);
  return (
    preferences.model === builtIn.model &&
    preferences.temperature === null &&
    preferences.maxTokens === null &&
    preferences.reasoningEffort === null
  );
}

/** The settings of `draft` that differ from `saved`, as a `PATCH` body. */
function changesOf(saved: Preferences, draft: Preferences): PreferencesPatch {
  const patch: PreferencesPatch = {};
  for (const phase of PHASES) {
    const [was, now] = [saved[phase], draft[phase]];
    const change: Partial<PhasePreferences> = {
      ...(now.model !== was.model && { model: now.model }),
      ...(now.temperature !== was.temperature && { temperature: now.temperature }),
      ...(now.maxTokens !== was.maxTokens && { maxTokens: now.maxTokens }),
      ...(now.reasoningEffort !== was.reasoningEffort && { reasoningEffort: now.reasoningEffort }),
    };
    if (Object.keys(change).length > 0) {
      patch[phase] = change;
    }
  }
  return patch;
}

/**
 * The "Model & Prompts" tab: the defaults every Interview starts from, for each of the six
 * phases. Edits are held as a draft and saved together, because the sliders would otherwise send a
 * request for every step of a drag. Unset temperature, max tokens and reasoning effort mean the
 * provider's own default. The system prompts are not here: they never leave the server.
 */
@Component({
  selector: 'app-model-defaults',
  providers: [provideIcons({ lucideInfo, lucideRotateCcw })],
  imports: [
    HlmBadgeImports,
    HlmButtonImports,
    HlmCardImports,
    HlmEmptyImports,
    HlmFieldImports,
    HlmLabelImports,
    HlmSelectImports,
    HlmSkeleton,
    HlmSlider,
    HlmSpinnerImports,
    HlmTooltipImports,
    NgIcon,
  ],
  templateUrl: './model-defaults.html',
})
export class ModelDefaults {
  private readonly api = inject(PreferencesApi);
  private readonly store = inject(PreferencesStore);

  protected readonly phases = PHASES;
  protected readonly phaseLabels = PHASE_LABELS;
  protected readonly phaseSteps = PHASE_STEPS;
  protected readonly phaseHints = PHASE_HINTS;
  protected readonly isSubStep = isSubStep;
  protected readonly reasoningEfforts = REASONING_EFFORTS;
  protected readonly defaultTemperature = DEFAULT_TEMPERATURE;
  protected readonly defaultMaxTokens = DEFAULT_MAX_TOKENS;
  protected readonly temperatureRange = TEMPERATURE_RANGE;
  protected readonly maxTokensRange = MAX_TOKENS_RANGE;

  /** What the server has. */
  protected readonly saved = this.store.preferences;
  /** What the page shows: `saved` plus the edits not saved yet. A new `saved` replaces it. */
  protected readonly draft = linkedSignal(() => this.saved());
  protected readonly loadError = this.store.loadError;

  private readonly changes = computed(() => {
    const [saved, draft] = [this.saved(), this.draft()];
    return saved && draft ? changesOf(saved, draft) : {};
  });
  /** Edits not saved yet; the page asks before it is left. */
  readonly dirty = computed(() => Object.keys(this.changes()).length > 0);

  protected readonly saving = signal(false);
  protected readonly saveError = signal<string | null>(null);

  protected readonly takenNote = takenNote;

  protected modelsFor(phase: Phase): readonly string[] {
    return phase === 'interviewerReview' ? JUDGE_MODELS : INTERVIEW_MODELS;
  }

  /** Whether `model` is shown but can't be picked for `phase`, as the judge rule forbids it. */
  protected isTaken(phase: Phase, model: string): boolean {
    const draft = this.draft();
    return !!draft && isModelTaken(phase, model, judgeRuleModels(draft));
  }

  /**
   * What resetting an interviewer phase also does, when its built-in model is the judge's: the
   * judge goes back to its own built-in model, so the rule holds. `null` when it does nothing else.
   */
  protected resetNote(phase: Phase): string | null {
    const draft = this.draft();
    const model = builtInPreferences(phase).model;
    return draft && isInterviewerPhase(phase) && draft.interviewerReview.model === model
      ? `${model} is the judge's model, so the judge goes back to ${DEFAULT_JUDGE_MODEL} too.`
      : null;
  }

  /** Whether the saved defaults of a phase differ from the built-in ones. */
  protected isCustomized(phase: Phase): boolean {
    const saved = this.saved();
    return !!saved && !isBuiltIn(phase, saved[phase]);
  }

  /** Whether the draft of a phase has anything to reset. */
  protected canReset(phase: Phase): boolean {
    const draft = this.draft();
    return !!draft && !isBuiltIn(phase, draft[phase]);
  }

  protected setModel(phase: Phase, raw: unknown): void {
    if (typeof raw === 'string' && raw !== '') {
      this.edit(phase, { model: raw });
    }
  }

  protected setEffort(phase: Phase, raw: unknown): void {
    this.edit(phase, {
      reasoningEffort: REASONING_EFFORTS.find((effort) => effort === raw) ?? null,
    });
  }

  protected setTemperature(phase: Phase, [value]: number[]): void {
    this.edit(phase, { temperature: value === undefined ? null : Number(value.toFixed(2)) });
  }

  protected setMaxTokens(phase: Phase, [value]: number[]): void {
    this.edit(phase, { maxTokens: value === undefined ? null : Math.round(value) });
  }

  protected clear(phase: Phase, setting: 'temperature' | 'maxTokens'): void {
    this.edit(phase, { [setting]: null });
  }

  protected reset(phase: Phase): void {
    this.edit(phase, builtInPreferences(phase));
  }

  protected discard(): void {
    this.draft.set(this.saved());
    this.saveError.set(null);
  }

  protected async save(): Promise<void> {
    const patch = this.changes();
    if (this.saving() || Object.keys(patch).length === 0) {
      return;
    }
    this.saveError.set(null);
    this.saving.set(true);
    try {
      this.store.replace(await firstValueFrom(this.api.update(patch)));
      toast.success('Defaults saved');
    } catch (err) {
      this.saveError.set(toApiError(err).message);
    } finally {
      this.saving.set(false);
    }
  }

  protected retry(): void {
    this.store.reload();
  }

  private edit(phase: Phase, change: Partial<PhasePreferences>): void {
    const draft = this.draft();
    if (!draft) {
      return;
    }
    const edited = { ...draft, [phase]: { ...draft[phase], ...change } };
    const next = this.withoutCollidingJudge(edited);
    this.draft.set(next);
    if (next.interviewerReview.model !== edited.interviewerReview.model) {
      toast.info(
        `The judge went back to ${DEFAULT_JUDGE_MODEL}: it can't use a model that runs the interview.`,
      );
    }
  }

  /**
   * The picker does not offer a colliding model, so only resetting an interviewer phase to a
   * built-in model the judge uses gets here. The judge goes back to its built-in model, which
   * no interviewer phase can use (ADR 0009).
   */
  private withoutCollidingJudge(preferences: Preferences): Preferences {
    return collidingPhases(judgeRuleModels(preferences)).length > 0
      ? {
          ...preferences,
          interviewerReview: { ...preferences.interviewerReview, model: DEFAULT_JUDGE_MODEL },
        }
      : preferences;
  }
}

function judgeRuleModels(preferences: Preferences): JudgeRuleModels {
  return resolveRuleModels((phase) => preferences[phase].model);
}
