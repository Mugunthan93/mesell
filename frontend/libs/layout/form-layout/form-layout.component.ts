import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MEE_GAP_TOKEN, type MeeFormMaxWidth, type MeeLayoutGap } from '../layout.types';

/**
 * Tailwind max-width class map for `mee-form-layout`.
 * Tighter than `mee-page` — single-column forms read best ≤ ~640px.
 */
const FORM_MAX_WIDTH_CLASS: Record<MeeFormMaxWidth, string> = {
  sm:   'max-w-sm',
  md:   'max-w-screen-sm',   // ~640px — comfortable single-column form width
  lg:   'max-w-screen-md',
  full: 'max-w-none',
};

/**
 * `mee-form-layout` — vertical form field column.
 *
 * A vertical flex column tuned for stacked form fields: consistent field
 * gap, full-width children, and an optional constrained reading width so
 * long forms stay legible on desktop without stretching to the viewport edge.
 *
 * Distinct from `mee-stack` (which is generic) because `mee-form-layout`
 * encodes form-specific defaults: larger default gap, full-width children,
 * and a reading-width cap — so a feature author writes `<mee-form-layout>`
 * once without re-deriving the right stack props per form.
 *
 * Styling idiom: Tailwind for max-width + flex column + `w-full` on children
 * via `[&>*]:w-full`; `[style.gap]` binding to `var(--mee-space-N)` tokens.
 *
 * @example
 * ```html
 * <mee-form-layout gap="lg" maxWidth="md">
 *   <mee-input label="Product name" formControlName="name" />
 *   <mee-input label="MRP"          formControlName="mrp" />
 *   <mee-select label="Category"    formControlName="category" />
 * </mee-form-layout>
 * ```
 */
@Component({
  selector: 'mee-form-layout',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      [class]="hostClass()"
      [style.gap]="gapValue()"
    >
      <ng-content />
    </div>
  `,
  styles: [`:host { display: block; }`],
})
export class MeeFormLayoutComponent {
  /** Vertical gap between form fields. Default: 'lg'. */
  readonly gap = input<MeeLayoutGap>('lg');

  /** Max width of the form column. Default: 'md' (~640px). */
  readonly maxWidth = input<MeeFormMaxWidth>('md');

  /** Derived Tailwind classes for the form column container. */
  readonly hostClass = computed<string>(() => {
    const mw = FORM_MAX_WIDTH_CLASS[this.maxWidth()];
    // [&>*]:w-full ensures every projected form field stretches to column width
    return `flex flex-col w-full ${mw} [&>*]:w-full`;
  });

  /** Token-driven gap value applied via `[style.gap]`. */
  readonly gapValue = computed<string>(() => MEE_GAP_TOKEN[this.gap()]);
}
