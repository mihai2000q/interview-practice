import {
  afterRenderEffect,
  Component,
  ElementRef,
  input,
  linkedSignal,
  viewChild,
} from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideLightbulb } from '@ng-icons/lucide';
import { HlmCollapsibleImports } from '@spartan-ng/helm/collapsible';

/**
 * A coaching hint in a collapsible card, closed until the candidate asks for it so they try
 * first. Once the question is answered it closes again (and can still be reopened).
 */
@Component({
  selector: 'app-hint-card',
  imports: [HlmCollapsibleImports, NgIcon],
  providers: [provideIcons({ lucideLightbulb })],
  templateUrl: './hint-card.html',
  host: { class: 'block w-full' },
})
export class HintCard {
  readonly hint = input.required<string>();
  /** The candidate has replied to the question this hint belongs to. */
  readonly answered = input(false);

  protected readonly open = linkedSignal({ source: this.answered, computation: () => false });
  private readonly content = viewChild.required<ElementRef<HTMLElement>>('content');

  constructor() {
    // The card sits at the bottom of the transcript, so bring what opens into view.
    afterRenderEffect(() => {
      if (this.open()) {
        this.scrollIntoView();
      }
    });
  }

  /** The card grows over the transition, so look again once it has finished. */
  protected onTransitionEnd(event: TransitionEvent): void {
    if (this.open() && event.propertyName === 'height') {
      this.scrollIntoView();
    }
  }

  private scrollIntoView(): void {
    this.content().nativeElement.scrollIntoView?.({ block: 'nearest' });
  }
}
