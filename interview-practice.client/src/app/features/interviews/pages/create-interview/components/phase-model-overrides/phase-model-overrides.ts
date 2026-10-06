import { DOCUMENT } from '@angular/common';
import { Component, computed, DestroyRef, inject, input } from '@angular/core';
import { FieldTree } from '@angular/forms/signals';
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
} from '@app/features/interviews/models/phase-settings.schema';
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

/** The phases whose output is the interviewer the judge scores (ADR 0009). */
const INTERVIEWER_PHASES = ['questionPlan', 'liveConversation'] as const;

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
  /**
   * The judge the Preferences give this Interview, while it has no judge override of its own; an
   * interview model may not be it either (ADR 0009), and the server would answer `409`.
   */
  private readonly inheritedJudgeModel = computed(() =>
    this.value().interviewerReview?.model
      ? undefined
      : this.preferences.phase('interviewerReview').model,
  );
  private readonly judgeModels = computed(() => {
    const taken = this.interviewerModels(this.value());
    return JUDGE_MODELS.filter((model) => !taken.has(model));
  });

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
    if (phase === 'interviewerReview') {
      return this.judgeModels();
    }
    const inheritedJudge = this.inheritedJudgeModel();
    return phase === 'questionPlan' || phase === 'liveConversation'
      ? INTERVIEW_MODELS.filter((model) => model !== inheritedJudge)
      : INTERVIEW_MODELS;
  }

  /** What the phase starts from: the Preferences default, to which this Interview's choices are layered. */
  protected defaultOf(phase: Phase): PhasePreferences {
    return this.preferences.phase(phase);
  }

  protected defaultModelLabel(phase: Phase): string {
    return `Default (${this.defaultOf(phase).model})`;
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
    field.value.update((current) => this.applyChange(current, phase, change));
    field.markAsDirty();
  }

  /**
   * Applies one edit to a phase and returns the next overrides: unset (`undefined`) values are
   * removed and a phase left with nothing set is removed entirely. The judge rule (ADR 0009) is
   * then restored: an edit to an interview phase clears a judge that now collides with it, and an
   * edit to the judge (resetting it to "Default" can bring back one the interview models already
   * use) clears the interview model overrides that collide with it.
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
    return phase === 'interviewerReview'
      ? this.dropCollidingInterviewers(next)
      : this.dropCollidingJudge(next);
  }

  /**
   * The judge must never be the model that ran the interview (ADR 0009). The "interview" is the
   * question plan and the live conversation; a phase without an override uses the default model.
   * The server enforces the same rule (`app/interviews/model_rules.py`) as a safety net.
   */
  private interviewerModels(settings: PhaseSettingsOverride): Set<string> {
    return new Set(
      INTERVIEWER_PHASES.map(
        (phase) => settings[phase]?.model ?? this.preferences.phase(phase).model,
      ),
    );
  }

  /** Clears the judge's model (and the judge entry, if nothing else is set) when it now collides. */
  private dropCollidingJudge(settings: PhaseSettingsOverride): PhaseSettingsOverride {
    const model = settings.interviewerReview?.model;
    return model && this.interviewerModels(settings).has(model)
      ? this.withoutModel(settings, 'interviewerReview')
      : settings;
  }

  /**
   * Clears the model overrides of the interview phases that run on the judge's model. Only the
   * overrides can collide: the Preferences defaults never do, so a cleared phase falls back to a
   * model other than the judge's.
   */
  private dropCollidingInterviewers(settings: PhaseSettingsOverride): PhaseSettingsOverride {
    const judge =
      settings.interviewerReview?.model ?? this.preferences.phase('interviewerReview').model;
    return INTERVIEWER_PHASES.reduce(
      (next, phase) => (next[phase]?.model === judge ? this.withoutModel(next, phase) : next),
      settings,
    );
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
