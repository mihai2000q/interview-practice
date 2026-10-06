import { NgOptimizedImage } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideBriefcase, lucideBuilding2, lucideTrendingUp } from '@ng-icons/lucide';
import { HlmAvatarImports } from '@spartan-ng/helm/avatar';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmProgressImports } from '@spartan-ng/helm/progress';
import { HlmCard, HlmCardContent, HlmCardHeader, HlmCardTitle } from '@spartan-ng/helm/card';
import {
  INTERVIEWER_ROLES,
  INTERVIEWER_TONES,
  SENIORITIES,
  interviewSettings,
  labelOf,
  SENIORITY_ICON,
} from '@app/features/interviews/models/interview.options';
import { Interview } from '@app/features/interviews/models/interview.schema';
import { initialsOf } from '@app/features/interviews/utils/initials';

@Component({
  selector: 'app-interviewer-panel',
  imports: [
    HlmAvatarImports,
    HlmBadge,
    HlmCard,
    HlmCardContent,
    HlmCardHeader,
    HlmCardTitle,
    HlmProgressImports,
    NgIcon,
    NgOptimizedImage,
  ],
  providers: [provideIcons({ lucideBriefcase, lucideBuilding2, lucideTrendingUp })],
  templateUrl: './interviewer-panel.html',
})
export class InterviewerPanel {
  readonly interview = input.required<Interview>();
  readonly personaImageUrl = input<string | null>(null);
  /** Interviewer messages in the Q&A phase; each counts as one question. */
  readonly questionsAsked = input.required<number>();

  private readonly roleLabel = labelOf(INTERVIEWER_ROLES);
  private readonly seniorityLabel = labelOf(SENIORITIES);
  private readonly toneLabel = labelOf(INTERVIEWER_TONES);
  protected readonly initials = computed(() => initialsOf(this.interview().personaName));
  protected readonly role = computed(() => this.roleLabel(this.interview().interviewerRole));
  protected readonly tone = computed(() => this.toneLabel(this.interview().tone));
  protected readonly progress = computed(() => {
    const target = this.interview().targetQuestionCount;
    const asked = Math.min(this.questionsAsked(), target);
    return { asked, target, percent: Math.round((asked / target) * 100) };
  });
  protected readonly inQa = computed(() => this.interview().phase === 'qa');
  /** What the interview is for, shown first and set apart from the settings below it. */
  protected readonly job = computed(() => {
    const interview = this.interview();
    return [
      { label: 'Position', value: interview.jobTitle, icon: 'lucideBriefcase' },
      ...(interview.companyName
        ? [{ label: 'Company', value: interview.companyName, icon: 'lucideBuilding2' }]
        : []),
      { label: 'Seniority', value: this.seniorityLabel(interview.seniority), icon: SENIORITY_ICON },
    ];
  });
  protected readonly details = computed(() => {
    const interview = this.interview();
    return [
      ...interviewSettings(interview, { withSeniority: false }),
      { label: 'Coaching helpers', value: interview.coachingHelpersEnabled ? 'On' : 'Off' },
    ];
  });
}
