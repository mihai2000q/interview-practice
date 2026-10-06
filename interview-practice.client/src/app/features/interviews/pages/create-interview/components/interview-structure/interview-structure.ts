import { Component, input } from '@angular/core';
import { HlmCard, HlmCardContent, HlmCardHeader, HlmCardTitle } from '@spartan-ng/helm/card';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideCode, lucideMessageSquare, lucideSlidersHorizontal } from '@ng-icons/lucide';
import { FieldTree, FormField } from '@angular/forms/signals';
import { CreateInterviewModel } from '@app/features/interviews/pages/create-interview/models/create-interview.schema';
import { HlmField, HlmFieldGroup, HlmFieldLabel } from '@spartan-ng/helm/field';
import { HlmToggleGroup, HlmToggleGroupItem } from '@spartan-ng/helm/toggle-group';
import {
  DIFFICULTIES,
  INTERVIEW_TYPES,
  RESPONSE_STYLES,
} from '@app/features/interviews/models/interview.options';
import { DIFFICULTY_DEFAULTS } from '@app/features/interviews/pages/create-interview/models/create-interview.defaults';
import { HlmBadgeImports } from '@spartan-ng/helm/badge';
import { HlmSlider } from '@spartan-ng/helm/slider';
import { MAX_QUESTION_COUNT } from '@app/features/interviews/interviews.constants';

@Component({
  providers: [provideIcons({ lucideCode, lucideMessageSquare, lucideSlidersHorizontal })],
  imports: [
    FormField,
    HlmCard,
    HlmCardContent,
    HlmCardHeader,
    HlmCardTitle,
    NgIcon,
    HlmField,
    HlmFieldGroup,
    HlmFieldLabel,
    HlmToggleGroup,
    HlmToggleGroupItem,
    HlmBadgeImports,
    HlmSlider,
  ],
  selector: 'app-interview-structure',
  templateUrl: './interview-structure.html',
})
export class InterviewStructure {
  readonly interviewForm = input.required<FieldTree<CreateInterviewModel>>();
  protected readonly interviewTypes = INTERVIEW_TYPES;
  protected readonly difficulties = DIFFICULTIES;
  protected readonly responseStyles = RESPONSE_STYLES;
  protected readonly maxQuestionCount = MAX_QUESTION_COUNT;

  /** Picking a difficulty seeds the question count, tone, type, response style and helpers; all stay editable. */
  protected onDifficultyChange(difficulty: unknown): void {
    if (typeof difficulty !== 'string' || !(difficulty in DIFFICULTY_DEFAULTS)) {
      return;
    }
    const defaults = DIFFICULTY_DEFAULTS[difficulty as keyof typeof DIFFICULTY_DEFAULTS];
    const form = this.interviewForm();
    form.targetQuestionCount().value.set(defaults.targetQuestionCount);
    form.targetQuestionCount().markAsDirty();
    form.tone().value.set(defaults.tone);
    form.tone().markAsDirty();
    form.interviewType().value.set(defaults.interviewType);
    form.interviewType().markAsDirty();
    form.responseStyle().value.set(defaults.responseStyle);
    form.responseStyle().markAsDirty();
    form.coachingHelpersEnabled().value.set(defaults.coachingHelpersEnabled);
    form.coachingHelpersEnabled().markAsDirty();
  }

  /** The slider works with `number[]` (it supports ranges); we only ever have one thumb. */
  protected setQuestionCount([count]: number[]): void {
    if (count === undefined) {
      return;
    }
    const field = this.interviewForm().targetQuestionCount();
    field.value.set(count);
    field.markAsDirty();
  }
}
