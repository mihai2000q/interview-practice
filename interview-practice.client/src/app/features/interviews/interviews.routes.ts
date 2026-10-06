import { Routes } from '@angular/router';
import { leaveConfirmationGuard } from '@app/core/guards/leave-confirmation-guard';
import { showsHistory } from '@app/core/layout/route-context';
import { crumbs } from '@app/core/layout/topbar/crumbs';

export const INTERVIEWS_ROUTES: Routes = [
  {
    path: 'new',
    canDeactivate: [leaveConfirmationGuard],
    data: crumbs(() => [{ label: 'New interview' }]),
    loadComponent: () =>
      import('./pages/create-interview/create-interview').then((m) => m.CreateInterview),
  },
  {
    path: ':id/results',
    data: {
      ...crumbs(({ id }) => [
        { label: 'Interview', link: `/interviews/${id}` },
        { label: 'Results' },
      ]),
      ...showsHistory(),
    },
    loadComponent: () =>
      import('./pages/interview-results/interview-results').then((m) => m.InterviewResults),
  },
  {
    path: ':id',
    canDeactivate: [leaveConfirmationGuard],
    data: crumbs(() => [{ label: 'Interview' }]),
    loadComponent: () =>
      import('./pages/interview-session/interview-session').then((m) => m.InterviewSession),
  },
];
