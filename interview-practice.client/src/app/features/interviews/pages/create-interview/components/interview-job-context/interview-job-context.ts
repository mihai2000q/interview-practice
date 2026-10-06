import { Component, input } from '@angular/core';
import { FieldTree, FormField } from '@angular/forms/signals';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideBriefcase } from '@ng-icons/lucide';
import { HlmCard, HlmCardContent, HlmCardHeader, HlmCardTitle } from '@spartan-ng/helm/card';
import { HlmField, HlmFieldError, HlmFieldGroup, HlmFieldLabel } from '@spartan-ng/helm/field';
import { HlmInput } from '@spartan-ng/helm/input';
import { HlmToggleGroupImports } from '@spartan-ng/helm/toggle-group';
import { SENIORITIES } from '@app/features/interviews/models/interview.options';
import { CreateInterviewModel } from '@app/features/interviews/pages/create-interview/models/create-interview.schema';

@Component({
  providers: [provideIcons({ lucideBriefcase })],
  imports: [
    HlmFieldError,
    FormField,
    HlmCard,
    HlmCardContent,
    HlmCardHeader,
    HlmCardTitle,
    HlmField,
    HlmFieldGroup,
    HlmFieldLabel,
    HlmInput,
    HlmToggleGroupImports,
    NgIcon,
  ],
  selector: 'app-interview-job-context',
  templateUrl: './interview-job-context.html',
})
export class InterviewJobContext {
  readonly interviewForm = input.required<FieldTree<CreateInterviewModel>>();

  protected readonly seniorities = SENIORITIES;
}
