import { DOCUMENT } from '@angular/common';
import { Component, computed, DestroyRef, inject, input } from '@angular/core';
import { FieldTree } from '@angular/forms/signals';
import { toast } from '@spartan-ng/brain/sonner';
import { HlmLabelImports } from '@spartan-ng/helm/label';
import { HlmSelectImports } from '@spartan-ng/helm/select';
import {
  DEFAULT_MAX_TOKENS,
  DEFAULT_TEMPERATURE,
  compactPhaseSettings,
  INTERVIEW_MODELS,
  JUDGE_MODELS,
  MAX_TOKENS_RANGE,
  Phase,
  PHASE_HINTS,
  PHASE_LABELS,
  PHASE_STEPS,
  PHASES,
  PhaseSettings,
  PhaseSettingsOverride,
  isSubStep,
  REASONING_EFFORTS,
  TEMPERATURE_RANGE,
} from '@app/core/phase-settings/phase-settings.schema';
import {
  collidingPhases,
  isModelTaken,
  JudgeRuleModels,
  resolveRuleModels,
  takenNote,
} from '@app/core/phase-settings/judge-rule';
import { PhasePreferences } from '@app/features/preferences/models/preferences.schema';
import { PreferencesStore } from '@app/features/preferences/services/preferences-store';
import { CreateInterviewModel } from '@app/features/interviews/pages/create-interview/models/create-interview.schema';
import {
  HlmCard,
  HlmCardContent,
  HlmCardHeader,
  HlmCardImports,
  HlmCardTitle,
} from '@spartan-ng/helm/card';
import { HlmFieldGroup, HlmFieldImports } from '@spartan-ng/helm/field';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideChevronDown, lucideInfo, lucideWrench } from '@ng-icons/lucide';
import { HlmCollapsibleImports } from '@spartan-ng/helm/collapsible';
import { HlmBadgeImports } from '@spartan-ng/helm/badge';
import { HlmSlider } from '@spartan-ng/helm/slider';
import { HlmTooltipImports } from '@spartan-ng/helm/tooltip';

/** The section's collapse takes this long; scrolling to its end waits for it. */
const COLLAPSE_TRANSITION_MS = 300;
const SCROLL_DELAY_MS = COLLAPSE_TRANSITION_MS + 20;

@Component({
  selector: 'app-phase-model-overrides',
  providers: [provideIcons({ lucideChevronDown, lucideInfo, lucideWrench })],
  imports: [
    HlmLabelImports,
    HlmSelectImports,
    HlmCard,
    HlmCardContent,
    HlmCardHeader,
    HlmCardTitle,
    HlmFieldGroup,
    NgIcon,
    HlmBadgeImports,
    HlmCardImports,
    HlmFieldImports,
    HlmSlider,
    HlmCollapsibleImports,
    HlmTooltipImports,
  ],
  templateUrl: './phase-model-overrides.html',
})
export class PhaseModelOverrides {
  readonly interviewForm = input.required<FieldTree<CreateInterviewModel>>();
  protected readonly phases = PHASES;
  protected readonly phaseLabels = PHASE_LABELS;
  protected readonly phaseSteps = PHASE_STEPS;
  protected readonly phaseHints = PHASE_HINTS;
  protected readonly isSubStep = isSubStep;
  protected readonly reasoningEfforts = REASONING_EFFORTS;
  protected readonly temperatureRange = TEMPERATURE_RANGE;
  protected readonly maxTokensRange = MAX_TOKENS_RANGE;
  private readonly preferences = inject(PreferencesStore);
  private readonly document = inject(DOCUMENT);
  private scrollTimer: ReturnType<typeof setTimeout> | undefined;
  private readonly field = computed(() => this.interviewForm().phaseSettings());
  private readonly value = computed(() => this.field().value());
  protected readonly takenNote = takenNote;
  /** The models the judge and the interviewer run on now, chosen here or from the Preferences. */
  private readonly ruleModels = computed(() => this.judgeRuleModels(this.value()));

  constructor() {
    inject(DestroyRef).onDestroy(() => clearTimeout(this.scrollTimer));
  }

  /** Opening the section grows the page; scroll to the bottom once the transition is done. */
  protected onExpandedChange(expanded: boolean): void {
    clearTimeout(this.scrollTimer);
    if (!expanded) {
      return;
    }
    this.scrollTimer = setTimeout(
      () =>
        this.document.defaultView?.scrollTo({
          top: this.document.documentElement.scrollHeight,
          behavior: 'smooth',
        }),
      SCROLL_DELAY_MS,
    );
  }

  protected modelsFor(phase: Phase): readonly string[] {
    return phase === 'interviewerReview' ? JUDGE_MODELS : INTERVIEW_MODELS;
  }

  /** Whether `model` is shown but can't be picked for `phase`, as the judge rule forbids it. */
  protected isTaken(phase: Phase, model: string): boolean {
    return isModelTaken(phase, model, this.ruleModels());
  }

  /** What the phase starts from: the Preferences default, to which this Interview's choices are layered. */
  protected defaultOf(phase: Phase): PhasePreferences {
    return this.preferences.phase(phase);
  }

  /** Without the Preferences the default's model is not known: it is not shown as the built-in one. */
  protected defaultModelLabel(phase: Phase): string {
    return this.preferences.ready() ? `Default (${this.defaultOf(phase).model})` : 'Default';
  }

  /** "Default", with the value a Preference gives it if there is one. */
  protected reasoningLabel(phase: Phase): string {
    const effort = this.defaultOf(phase).reasoningEffort;
    return effort === null ? 'Default reasoning' : `Default reasoning (${effort})`;
  }

  protected defaultLabel(value: number | string | null): string {
    return value === null ? 'Default' : `Default (${value})`;
  }

  /** Where the slider rests while the setting is unset: at the default, else mid-way. */
  protected temperatureAt(phase: Phase): number {
    return (
      this.current(phase).temperature ?? this.defaultOf(phase).temperature ?? DEFAULT_TEMPERATURE
    );
  }

  protected maxTokensAt(phase: Phase): number {
    return this.current(phase).maxTokens ?? this.defaultOf(phase).maxTokens ?? DEFAULT_MAX_TOKENS;
  }

  protected current(phase: Phase): PhaseSettings {
    return this.value()[phase] ?? {};
  }

  protected setModel(phase: Phase, raw: unknown): void {
    this.set(phase, { model: this.textOrUndefined(raw) });
  }

  protected setEffort(phase: Phase, raw: unknown): void {
    this.set(phase, { reasoningEffort: REASONING_EFFORTS.find((effort) => effort === raw) });
  }

  protected setTemperature(phase: Phase, values: number[]): void {
    this.set(phase, { temperature: this.sliderNumber(values) });
  }

  protected setMaxTokens(phase: Phase, values: number[]): void {
    this.set(phase, { maxTokens: this.sliderNumber(values) });
  }

  /** The select emits '' or null for "Default"; we store "not set". */
  private textOrUndefined(raw: unknown): string | undefined {
    return typeof raw === 'string' && raw !== '' ? raw : undefined;
  }

  /** The slider emits `number[]` (it supports ranges); we only ever have one thumb. */
  private sliderNumber([value]: number[]): number | undefined {
    return value === undefined ? undefined : Number(value.toFixed(2));
  }

  private set(phase: Phase, change: Partial<PhaseSettings>): void {
    const field = this.field();
    const edited = this.applyChange(field.value(), phase, change);
    const next = this.restoreJudgeRule(edited, phase);
    field.value.set(next);
    field.markAsDirty();
    const reset = PHASES.filter((other) => edited[other]?.model !== next[other]?.model);
    if (reset.length > 0) {
      const named = reset.map(
        (other) =>
          `${PHASE_LABELS[other]} (${edited[other]?.model} → ${this.modelIn(next, other) ?? 'default'})`,
      );
      toast.info(
        `The judge and the interviewer can't share a model, so these went back to the default ` +
          `model: ${new Intl.ListFormat('en').format(named)}.`,
      );
    }
  }

  /**
   * Applies one edit to a phase and returns the next overrides: unset (`undefined`) values are
   * removed and a phase left with nothing set is removed entirely.
   */
  private applyChange(
    settings: PhaseSettingsOverride,
    phase: Phase,
    change: Partial<PhaseSettings>,
  ): PhaseSettingsOverride {
    const merged = compactPhaseSettings({ ...settings[phase], ...change });
    const next: PhaseSettingsOverride = { ...settings };
    if (merged) {
      next[phase] = merged;
    } else {
      delete next[phase];
    }
    return next;
  }

  /**
   * The models in effect for `settings`: an override, else the Preferences default (which is not
   * known until they are loaded).
   */
  private judgeRuleModels(settings: PhaseSettingsOverride): JudgeRuleModels {
    return resolveRuleModels((phase) => this.modelIn(settings, phase));
  }

  /** The model `phase` runs on under `settings`, `undefined` while the default is not known. */
  private modelIn(settings: PhaseSettingsOverride, phase: Phase): string | undefined {
    return (
      settings[phase]?.model ??
      (this.preferences.ready() ? this.preferences.phase(phase).model : undefined)
    );
  }

  /**
   * The pickers don't offer a colliding model, but a "Default" can bring one back: the judge's
   * back to a Preferences model an interviewer override already uses, or an interviewer's back to
   * a Preferences model the judge override uses. The phase that was not edited gives way, so the
   * choice just made stands (ADR 0009). An override that gives way falls back to a Preferences
   * model, which can collide with yet another override, so this goes on until none does.
   */
  private restoreJudgeRule(settings: PhaseSettingsOverride, edited: Phase): PhaseSettingsOverride {
    const colliding = collidingPhases(this.judgeRuleModels(settings));
    // The judge gives way first, as it is the one that has to move off the interviewer's model.
    const giveWay = colliding.length
      ? (['interviewerReview', ...colliding] as const).find(
          (phase) => phase !== edited && settings[phase]?.model !== undefined,
        )
      : undefined;
    // Each step removes a model override, so this ends.
    return giveWay ? this.restoreJudgeRule(this.withoutModel(settings, giveWay), edited) : settings;
  }

  /** `settings` without the model of `phase`, and without the phase itself if nothing else is set. */
  private withoutModel(settings: PhaseSettingsOverride, phase: Phase): PhaseSettingsOverride {
    const rest = compactPhaseSettings({ ...settings[phase], model: undefined });
    const next = { ...settings };
    if (rest) {
      next[phase] = rest;
    } else {
      delete next[phase];
    }
    return next;
  }
}
