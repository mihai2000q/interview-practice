import { Component, input } from '@angular/core';

/** Placeholder until the evaluation is shown here (docs/overview.md). `id` comes from the route. */
@Component({
  selector: 'app-interview-results',
  templateUrl: './interview-results.html',
})
export class InterviewResults {
  readonly id = input.required<string>();
}
