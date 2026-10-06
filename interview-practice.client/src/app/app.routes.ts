import { Routes } from '@angular/router';
import { showsHistory } from './core/layout/route-context';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    data: showsHistory(),
    loadComponent: () => import('./features/home/pages/home/home').then((m) => m.Home),
  },
  {
    path: 'interviews',
    loadChildren: () =>
      import('./features/interviews/interviews.routes').then((m) => m.INTERVIEWS_ROUTES),
  },
];
