import { Routes } from '@angular/router';
import { leaveConfirmationGuard } from '@app/core/guards/leave-confirmation-guard';

export const INTERVIEWS_ROUTES: Routes = [
  {
    path: 'new',
    canDeactivate: [leaveConfirmationGuard],
    loadComponent: () =>
      import('./pages/create-interview/create-interview').then((m) => m.CreateInterview),
  },
  {
    path: ':id/results',
    loadComponent: () =>
      import('./pages/interview-results/interview-results').then((m) => m.InterviewResults),
  },
  {
    path: ':id',
    canDeactivate: [leaveConfirmationGuard],
    loadComponent: () =>
      import('./pages/interview-session/interview-session').then((m) => m.InterviewSession),
  },
];
