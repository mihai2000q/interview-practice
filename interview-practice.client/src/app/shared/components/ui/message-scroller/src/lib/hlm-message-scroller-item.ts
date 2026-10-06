import { Directive } from '@angular/core';
import { BrnMessageScrollerItem } from '@spartan-ng/brain/message-scroller';
import { classes } from '@spartan-ng/helm/utils';

@Directive({
  selector: '[hlmMessageScrollerItem],hlm-message-scroller-item',
  hostDirectives: [
    {
      directive: BrnMessageScrollerItem,
      inputs: ['messageId', 'scrollAnchor'],
    },
  ],
  host: {
    'data-slot': 'message-scroller-item',
  },
})
export class HlmMessageScrollerItem {
  constructor() {
    // No `content-visibility: auto` (Spartan's default): it holds off-screen rows at an estimated
    // height until they scroll into range, so scrolling up makes the transcript jump.
    classes(() => 'min-w-0 shrink-0');
  }
}
