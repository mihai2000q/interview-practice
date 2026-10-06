import { computed, inject, Service } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRouteSnapshot, NavigationEnd, Router } from '@angular/router';
import { filter, map, startWith } from 'rxjs';
import { Crumb, CRUMBS_KEY, CrumbsFn } from './topbar/crumbs';

/** The `data` key a route sets (`data: showsHistory()`) to get the history sidebar. */
export const HISTORY_KEY = 'history';

/** For a route's `data`: the page is shown with the history sidebar beside it. */
export function showsHistory(): { [HISTORY_KEY]: true } {
  return { [HISTORY_KEY]: true };
}

/**
 * What the active page says about the app around it, read from the deepest active route's `data`:
 * its breadcrumb trail and whether the history sidebar is shown. Pages declare these on their
 * routes, so the shell never needs to know which page it is looking at.
 */
@Service()
export class RouteContext {
  private readonly router = inject(Router);

  private readonly deepest = toSignal(
    this.router.events.pipe(
      filter((event) => event instanceof NavigationEnd),
      startWith(null),
      map(() => this.deepestRoute()),
    ),
    { requireSync: true },
  );

  readonly crumbs = computed<Crumb[]>(() => {
    const route = this.deepest();
    const crumbs: CrumbsFn | undefined = route.data[CRUMBS_KEY];
    return crumbs ? crumbs(route.params) : [];
  });
  readonly hasHistory = computed(() => this.deepest().data[HISTORY_KEY] === true);

  private deepestRoute(): ActivatedRouteSnapshot {
    let route = this.router.routerState.snapshot.root;
    while (route.firstChild) {
      route = route.firstChild;
    }
    return route;
  }
}
