import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideMessagesSquare, lucideMoon, lucideSun } from '@ng-icons/lucide';
import { HlmBreadcrumbImports } from '@spartan-ng/helm/breadcrumb';
import { HlmButtonImports } from '@spartan-ng/helm/button';
// From its own file, not the barrel (see app.ts).
import { HlmSidebarTrigger } from '@app/shared/components/ui/sidebar/src/lib/hlm-sidebar-trigger';
import { RouteContext } from '@app/core/layout/route-context';
import { AppTheme } from '@app/core/theme/app-theme';

/**
 * Always on screen. On the left, the app as the first step of a trail that says where the candidate
 * is (the page's route says so, see `crumbs`); on the right, the tools that apply everywhere.
 * What belongs to a flow (abandoning, starting an interview, preferences) stays out of it, so it
 * never needs to know whether a flow is running.
 */
@Component({
  selector: 'app-topbar',
  imports: [HlmBreadcrumbImports, HlmButtonImports, HlmSidebarTrigger, NgIcon, RouterLink],
  providers: [provideIcons({ lucideMessagesSquare, lucideMoon, lucideSun })],
  templateUrl: './topbar.html',
  host: { class: 'sticky top-0 z-40 block' },
})
export class Topbar {
  protected readonly route = inject(RouteContext);
  protected readonly theme = inject(AppTheme);
}
