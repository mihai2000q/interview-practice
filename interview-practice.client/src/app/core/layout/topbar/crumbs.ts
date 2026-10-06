import { Params } from '@angular/router';

/** One step of the topbar's trail. Without a `link` it is the current page. */
export interface Crumb {
  label: string;
  link?: string;
}

/** What a route puts in its `data` to say where it is, given its own route params. */
export type CrumbsFn = (params: Params) => Crumb[];

/** The `data` key the topbar reads. */
export const CRUMBS_KEY = 'crumbs';

/** For a route's `data`: `data: crumbs(({ id }) => [{ label: 'Interview' }])`. */
export function crumbs(fn: CrumbsFn): { [CRUMBS_KEY]: CrumbsFn } {
  return { [CRUMBS_KEY]: fn };
}
