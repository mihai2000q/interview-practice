import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideMessagesSquare, lucidePlus } from '@ng-icons/lucide';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';

/** What the page shows before the first interview: what this is, and how to start. */
@Component({
  selector: 'app-home-onboarding',
  imports: [HlmButtonImports, HlmEmptyImports, NgIcon, RouterLink],
  providers: [provideIcons({ lucideMessagesSquare, lucidePlus })],
  templateUrl: './home-onboarding.html',
})
export class HomeOnboarding {
  protected readonly steps = [
    {
      title: 'Describe the role',
      text: 'Add the job and, if you like, your CV and the job description.',
    },
    {
      title: 'Talk to the interviewer',
      text: 'An AI interviewer asks questions, one at a time, like the real thing.',
    },
    {
      title: 'Get your verdict',
      text: 'See a hire or no-hire decision, how well you used STAR, and what to work on.',
    },
  ];
}
