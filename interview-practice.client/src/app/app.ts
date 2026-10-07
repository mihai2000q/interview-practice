import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
// From its own file, not the barrel: the barrel would pull the whole sidebar (sheet, tooltips)
// into the initial bundle, and only the lazy history sidebar needs those.
import { HlmSidebarWrapper } from '@app/shared/components/ui/sidebar/src/lib/hlm-sidebar-wrapper';
import { HlmToasterImports } from '@spartan-ng/helm/sonner';
import { RouteContext } from './core/layout/route-context';
import { Topbar } from './core/layout/topbar/topbar';
import { HistorySidebar } from './features/history/history-sidebar/history-sidebar';
import { HistorySidebarWidth } from './features/history/history-sidebar/history-sidebar-width';

@Component({
  imports: [HistorySidebar, HlmSidebarWrapper, RouterOutlet, Topbar, HlmToasterImports],
  selector: 'app-root',
  templateUrl: './app.html',
})
export class App {
  protected readonly route = inject(RouteContext);
  protected readonly sidebarWidth = inject(HistorySidebarWidth);
}
