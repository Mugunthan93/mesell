import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MEE_GAP_TOKEN, type MeeLayoutGap } from '../layout.types';

/** Cross-axis alignment options for `mee-toolbar`. */
export type MeeToolbarAlign = 'start' | 'center' | 'end';

const ALIGN_CLASS: Record<MeeToolbarAlign, string> = {
  start:  'items-start',
  center: 'items-center',
  end:    'items-end',
};

/**
 * `mee-toolbar` — horizontal action bar with start and end regions.
 *
 * The default `<ng-content />` slot is the **start** (leading) region;
 * elements with the `[mee-toolbar-end]` attribute are projected into the
 * **end** (trailing) region, pushed right via `justify-between`.
 *
 * The toolbar wraps on small screens (`flex-wrap`) — mobile-first for
 * Tirupur sellers viewing on phones.
 *
 * Styling idiom: Tailwind for flex/wrap/justify + `[style.gap]` to
 * `var(--mee-space-N)` tokens.
 *
 * @example
 * ```html
 * <mee-toolbar gap="sm" align="center">
 *   <h2>Catalog list</h2>
 *   <div mee-toolbar-end>
 *     <mee-button label="New catalog" variant="primary" />
 *   </div>
 * </mee-toolbar>
 * ```
 */
@Component({
  selector: 'mee-toolbar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      [class]="hostClass()"
      [style.gap]="gapValue()"
    >
      <!-- Start (leading) region — default slot -->
      <ng-content />
      <!-- End (trailing) region — right-aligned -->
      <ng-content select="[mee-toolbar-end]" />
    </div>
  `,
  styles: [`:host { display: block; }`],
})
export class MeeToolbarComponent {
  /** Gap between items in the toolbar. Default: 'sm'. */
  readonly gap = input<MeeLayoutGap>('sm');

  /** Cross-axis alignment of toolbar items. Default: 'center'. */
  readonly align = input<MeeToolbarAlign>('center');

  /** Derived Tailwind classes for the flex container. */
  readonly hostClass = computed<string>(() => {
    const alignCls = ALIGN_CLASS[this.align()];
    return `flex flex-wrap justify-between ${alignCls}`;
  });

  /** Token-driven gap value applied via `[style.gap]`. */
  readonly gapValue = computed<string>(() => MEE_GAP_TOKEN[this.gap()]);
}
