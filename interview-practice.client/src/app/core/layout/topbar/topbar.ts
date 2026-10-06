import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRouteSnapshot, NavigationEnd, Router, RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideMessagesSquare, lucideMoon, lucideSun } from '@ng-icons/lucide';
import { HlmBreadcrumbImports } from '@spartan-ng/helm/breadcrumb';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { filter, map, startWith } from 'rxjs';
import { AppTheme } from '@app/core/theme/app-theme';
import { Crumb, CRUMBS_KEY, CrumbsFn } from './crumbs';

/**
 * Always on screen. On the left, the app as the first step of a trail that says where the candidate
 * is (the page's route says so, see `crumbs`); on the right, the tools that apply everywhere.
 * What belongs to a flow (abandoning, starting an interview, preferences) stays out of it, so it
 * never needs to know whether a flow is running.
 */
@Component({
  selector: 'app-topbar',
  imports: [HlmBreadcrumbImports, HlmButtonImports, NgIcon, RouterLink],
  providers: [provideIcons({ lucideMessagesSquare, lucideMoon, lucideSun })],
  templateUrl: './topbar.html',
  host: { class: 'sticky top-0 z-40 block' },
})
export class Topbar {
  private readonly router = inject(Router);
  protected readonly theme = inject(AppTheme);

  protected readonly crumbs = toSignal(
    this.router.events.pipe(
      filter((event) => event instanceof NavigationEnd),
      startWith(null),
      map(() => this.currentCrumbs()),
    ),
    { requireSync: true },
  );

  /** The deepest active route says where we are; a page without a trail is a top-level one. */
  private currentCrumbs(): Crumb[] {
    let route: ActivatedRouteSnapshot = this.router.routerState.snapshot.root;
    while (route.firstChild) {
      route = route.firstChild;
    }
    const crumbs: CrumbsFn | undefined = route.data[CRUMBS_KEY];
    return crumbs ? crumbs(route.params) : [];
  }
}
