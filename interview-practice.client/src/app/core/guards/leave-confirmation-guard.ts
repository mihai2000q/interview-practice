import { CanDeactivateFn } from '@angular/router';

/** A page that may need the candidate's confirmation before it is left. */
export interface ConfirmsLeaving {
  /** The question to ask before leaving, or `null` when leaving needs no confirmation. */
  leaveConfirmation(): string | null;
}

export const leaveConfirmationGuard: CanDeactivateFn<ConfirmsLeaving> = (component) => {
  const question = component.leaveConfirmation();
  return question === null || window.confirm(question);
};
