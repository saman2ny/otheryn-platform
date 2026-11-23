import { AbstractControl } from '@angular/forms';

const BASE =
  'w-full rounded-md border bg-white px-3 py-2.5 text-zinc-900 focus:ring-2 focus:outline-none';
const VALID = 'border-zinc-200 focus:border-teal-700 focus:ring-teal-100';
const INVALID = 'border-red-600 focus:border-red-600 focus:ring-red-100';

/** Tailwind class string for a form control, switching to the invalid palette once touched. */
export function formFieldClass(control: AbstractControl | null | undefined, extra = ''): string {
  const isInvalid = !!control && control.invalid && control.touched;
  return `${BASE} ${extra} ${isInvalid ? INVALID : VALID}`;
}
