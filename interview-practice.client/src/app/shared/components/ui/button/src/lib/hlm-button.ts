import {
  ApplicationRef,
  booleanAttribute,
  ComponentRef,
  createComponent,
  DestroyRef,
  Directive,
  effect,
  ElementRef,
  EnvironmentInjector,
  inject,
  input,
  signal,
  untracked,
} from '@angular/core';
import { BrnButton } from '@spartan-ng/brain/button';
import { classes } from '@spartan-ng/helm/utils';
import { cva, type VariantProps } from 'class-variance-authority';
import type { ClassValue } from 'clsx';
import { BUTTON_LABEL_CLASSES } from './hlm-button-label';
import { HlmButtonSpinner } from './hlm-button-spinner';
import { injectBrnButtonConfig } from './hlm-button.token';

export const buttonVariants = cva(
  "focus-visible:border-ring focus-visible:ring-ring/50 data-[matches-spartan-invalid=true]:ring-destructive/20 dark:data-[matches-spartan-invalid=true]:ring-destructive/40 data-[matches-spartan-invalid=true]:border-destructive dark:data-[matches-spartan-invalid=true]:border-destructive/50 rounded-md border border-transparent bg-clip-padding text-sm font-medium focus-visible:ring-3 active:not-aria-[haspopup]:not-data-loading:scale-93 data-[matches-spartan-invalid=true]:ring-3 [&_ng-icon:not([class*='text-'])]:text-[length:--spacing(4)] group/button cursor-pointer inline-flex shrink-0 items-center justify-center whitespace-nowrap transition-all outline-none select-none data-disabled:pointer-events-none data-disabled:opacity-50 [&_ng-icon]:pointer-events-none [&_ng-icon]:shrink-0",
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/80',
        outline:
          'border-border bg-background hover:bg-muted hover:text-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50 aria-expanded:bg-muted aria-expanded:text-foreground shadow-xs',
        secondary:
          'bg-secondary text-secondary-foreground aria-expanded:bg-secondary aria-expanded:text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)]',
        ghost:
          'hover:bg-muted hover:text-foreground dark:hover:bg-muted/50 aria-expanded:bg-muted aria-expanded:text-foreground',
        destructive:
          'bg-destructive/10 hover:bg-destructive/20 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/20 text-destructive focus-visible:border-destructive/40 dark:hover:bg-destructive/30',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default:
          'h-9 gap-1.5 px-2.5 in-data-[slot=button-group]:rounded-md has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2',
        xs: "h-6 gap-1 rounded-[min(var(--radius-md),8px)] px-2 text-xs in-data-[slot=button-group]:rounded-md has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_ng-icon:not([class*='text-'])]:text-[length:--spacing(3)]",
        sm: 'h-8 gap-1 rounded-[min(var(--radius-md),10px)] px-2.5 in-data-[slot=button-group]:rounded-md has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5',
        lg: 'h-10 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2',
        icon: 'size-9',
        'icon-xs':
          "size-6 rounded-[min(var(--radius-md),8px)] in-data-[slot=button-group]:rounded-md [&_ng-icon:not([class*='text-'])]:text-[length:--spacing(3)]",
        'icon-sm':
          'size-8 rounded-[min(var(--radius-md),10px)] in-data-[slot=button-group]:rounded-md',
        'icon-lg': 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export type ButtonVariants = VariantProps<typeof buttonVariants>;

@Directive({
  selector: 'button[hlmBtn], a[hlmBtn]',
  exportAs: 'hlmBtn',
  hostDirectives: [{ directive: BrnButton, inputs: ['disabled'] }],
  host: {
    'data-slot': 'button',
    '[attr.aria-busy]': 'loading() || null',
    '[attr.data-loading]': 'loading() || null',
    '[attr.data-loading-phase]': '_loadingPhase()',
  },
})
export class HlmButton {
  /**
   * Busy state for async actions. Unlike `disabled`, the button keeps focus and its look;
   * clicks are swallowed so the action can't fire twice. To swap the content for a spinner,
   * wrap the content in `hlmBtnLabel`; the button adds the spinner itself on first load.
   */
  public readonly loading = input(false, { transform: booleanAttribute });
  /** `loading` → the spinner slides in; `leaving` → it slides out again before returning to `idle`. */
  protected readonly _loadingPhase = signal<'idle' | 'loading' | 'leaving'>('idle');
  private readonly _config = injectBrnButtonConfig();
  public readonly variant = input<ButtonVariants['variant']>(this._config.variant);
  public readonly size = input<ButtonVariants['size']>(this._config.size);
  private readonly _additionalClasses = signal<ClassValue>('');
  private _leaveTimer: ReturnType<typeof setTimeout> | undefined;
  private readonly _host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly _environmentInjector = inject(EnvironmentInjector);
  private readonly _appRef = inject(ApplicationRef);
  private _spinner: ComponentRef<HlmButtonSpinner> | undefined;

  constructor() {
    effect(() => {
      const loading = this.loading();
      untracked(() => {
        clearTimeout(this._leaveTimer);
        if (loading) {
          this._ensureLabel();
          this._ensureSpinner();
          this._loadingPhase.set('loading');
        } else if (this._loadingPhase() === 'loading') {
          this._loadingPhase.set('leaving');
          this._leaveTimer = setTimeout(() => this._loadingPhase.set('idle'), 300);
        }
      });
    });
    // While loading, a click does nothing, whoever listens for it. A capture listener runs before
    // every other listener on the button (a `(click)` written on the same element included), which
    // a host `(click)` binding does not: that one ran after it and so was too late to stop it.
    const swallowClicksWhileLoading = (event: Event) => {
      if (this.loading()) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };
    this._host.addEventListener('click', swallowClicksWhileLoading, { capture: true });
    inject(DestroyRef).onDestroy(() => {
      this._host.removeEventListener('click', swallowClicksWhileLoading, { capture: true });
      clearTimeout(this._leaveTimer);
      this._spinner?.destroy();
    });

    classes(() => [
      buttonVariants({ variant: this.variant(), size: this.size() }),
      'relative data-loading:cursor-progress data-[loading-phase=loading]:overflow-hidden data-[loading-phase=leaving]:overflow-hidden',
      this._additionalClasses(),
    ]);
  }

  setClass(classes: string): void {
    this._additionalClasses.set(classes);
  }

  /**
   * Wraps plain text content in the label slot on first load. Content with control flow
   * (`@if`, `@for`) can't be moved without breaking Angular's insertion anchors, so it is left
   * alone and needs an explicit `hlmBtnLabel`.
   */
  private _ensureLabel(): void {
    const nodes = Array.from(this._host.childNodes);
    const hasLabel = this._host.querySelector(':scope > [data-slot="button-label"]');
    if (hasLabel || nodes.some((node) => node.nodeType === Node.COMMENT_NODE)) {
      return;
    }
    const label = this._host.ownerDocument.createElement('span');
    label.dataset['slot'] = 'button-label';
    label.className = BUTTON_LABEL_CLASSES;
    this._host.insertBefore(label, this._host.firstChild);
    nodes.forEach((node) => label.appendChild(node));
  }

  /** Adds the spinner slot on first load, unless the button already has its own. */
  private _ensureSpinner(): void {
    if (this._spinner || this._host.querySelector(':scope > [data-slot="button-spinner"]')) {
      return;
    }
    const element = this._host.ownerDocument.createElement('span');
    this._host.appendChild(element);
    this._spinner = createComponent(HlmButtonSpinner, {
      environmentInjector: this._environmentInjector,
      hostElement: element,
    });
    this._appRef.attachView(this._spinner.hostView);
  }
}
