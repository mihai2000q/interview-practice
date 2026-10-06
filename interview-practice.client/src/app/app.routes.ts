import { Routes } from '@angular/router';
import { leaveConfirmationGuard } from './core/guards/leave-confirmation-guard';
import { showsHistory } from './core/layout/route-context';
import { crumbs } from './core/layout/topbar/crumbs';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    data: showsHistory(),
    loadComponent: () => import('./features/home/pages/home/home').then((m) => m.Home),
  },
  {
    path: 'preferences',
    canDeactivate: [leaveConfirmationGuard],
    data: {
      ...crumbs(() => [{ label: 'Preferences' }]),
      ...showsHistory(),
    },
    loadComponent: () =>
      import('./features/preferences/pages/preferences/preferences').then((m) => m.Preferences),
  },
  {
    path: 'applications/:id',
    data: {
      ...crumbs(() => [{ label: 'Application' }]),
      ...showsHistory(),
    },
    loadComponent: () =>
      import('./features/applications/pages/application-overview/application-overview').then(
        (m) => m.ApplicationOverviewPage,
      ),
  },
  {
    path: 'interviews',
    loadChildren: () =>
      import('./features/interviews/interviews.routes').then((m) => m.INTERVIEWS_ROUTES),
  },
];
