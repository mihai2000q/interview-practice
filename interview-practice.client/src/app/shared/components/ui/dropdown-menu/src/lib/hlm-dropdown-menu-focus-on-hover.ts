import { InputModalityDetector } from '@angular/cdk/a11y';
import { CdkMenu, CdkMenuItem } from '@angular/cdk/menu';
import { Directive, inject, signal } from '@angular/core';

/**
 * @internal
 * Moves DOM focus to the hovered menu item. CDK menus only move focus with the keyboard, so on a pointer
 * the highlight would otherwise stay on the last keyboard-focused item (leaving two rows highlighted) and,
 * when a submenu closes, focus would fall to <body>, the menu stack would report no focus, and the whole
 * dropdown would collapse. Following the pointer with focus (Radix/shadcn behaviour) keeps a single
 * highlight and keeps focus inside the menu stack. setActiveMenuItem also syncs the key manager so keyboard
 * navigation continues from the hovered item.
 *
 * Applied as a host directive on every dropdown item type (item, checkbox, radio, sub-trigger).
 */
@Directive({
  selector: '[hlmDropdownMenuFocusOnHover]',
  host: {
    '(mouseenter)': '_focusOnHover()',
    '(focus)': '_onFocus()',
    // A key pressed on an item that is already focused (a menu with one item, say) moves no focus,
    // so there is no focus event to hear: the key itself says the keyboard is in charge.
    '(keydown)': '_keyboardFocus.set(true)',
    '(blur)': '_keyboardFocus.set(false)',
    // The highlight that follows keyboard focus hangs on this, not on `:focus-visible`: a menu
    // focuses its first item when it opens, and whether a browser calls that "visible" varies, so
    // an item could look hovered before it was (and then show no change, hence no transition,
    // when it really is hovered).
    '[attr.data-keyboard-focus]': '_keyboardFocus() ? "" : null',
  },
})
export class HlmDropdownMenuFocusOnHover {
  private readonly _cdkMenuItem = inject(CdkMenuItem, { self: true });
  private readonly _parentMenu = inject(CdkMenu, { optional: true });
  private readonly _inputModality = inject(InputModalityDetector);
  protected readonly _keyboardFocus = signal(false);
  private _movingFocusForHover = false;

  protected _focusOnHover(): void {
    // The pointer takes over from the keyboard: hovering highlights the item by itself.
    this._keyboardFocus.set(false);
    // Only skip synthetic hovers from touch taps; every real hover (mouse, or keyboard-then-hover,
    // which leaves the modality as 'keyboard') should move focus to keep a single highlight.
    if (this._inputModality.mostRecentModality === 'touch' || this._cdkMenuItem.disabled) {
      return;
    }
    this._movingFocusForHover = true;
    try {
      this._parentMenu?.setActiveMenuItem(this._cdkMenuItem);
    } finally {
      this._movingFocusForHover = false;
    }
  }

  protected _onFocus(): void {
    // Hover moves focus too (above), but hovering already highlights the item.
    this._keyboardFocus.set(
      !this._movingFocusForHover && this._inputModality.mostRecentModality === 'keyboard',
    );
  }
}
