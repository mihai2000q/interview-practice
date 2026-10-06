import type { Resource } from '@angular/core';

/**
 * The resource's value, or `undefined` while there is none (loading, idle or failed). Reading
 * `value()` of a failed resource throws, so a template or `computed` can't call it directly.
 */
export function valueOrUndefined<T>(resource: Resource<T | undefined>): T | undefined {
  return resource.hasValue() ? resource.value() : undefined;
}
