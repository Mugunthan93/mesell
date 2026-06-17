import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MEE_GAP_TOKEN, type MeeLayoutGap } from '../layout.types';

/** Direction of the stack flex axis. */
export type MeeStackDirection = 'vertical' | 'horizontal';

/** Cross-axis alignment for `mee-stack`. */
export type MeeStackAlign = 'start' | 'center' | 'end' | 'stretch';

/** Main-axis justification for `mee-stack`. */
export type MeeStackJustify = 'start' | 'center' | 'end' | 'between';

const DIRECTION_CLASS: Record<MeeStackDirection, string> = {
  vertical:   'flex-col',
  horizontal: 'flex-row',
};

const ALIGN_CLASS: Record<MeeStackAlign, string> = {
  start:   'items-start',
  center:  'items-center',
  end:     'items-end',
  stretch: 'items-stretch',
};

const JUSTIFY_CLASS: Record<MeeStackJustify, string> = {
  start:   'justify-start',
  center:  'justify-center',
  end:     'justify-end',
  between: 'justify-between',
};

/**
 * `mee-stack` — 1-D flex line with a consistent token-driven gap.
 *
 * The workhorse spacer primitive: lay out children in one direction
 * (column or row) with a gap. All alignment and justification options
 * are covered via signal inputs + `computed()` Tailwind class derivation.
 *
 * Styling idiom: Tailwind utilities for direction/align/justify/wrap +
 * `[style.gap]` binding to `var(--mee-space-N)` tokens.
 *
 * @example
 * ```html
 * <!-- Vertical stack of form fields -->
 * <mee-stack direction="vertical" gap="md">
 *   <mee-input label="Name" />
 *   <mee-input label="Phone" />
 * </mee-stack>
 *
 * <!-- Horizontal row of action buttons -->
 * <mee-stack direction="horizontal" gap="sm" justify="end">
 *   <mee-button label="Cancel" variant="ghost" />
 *   <mee-button label="Save"   variant="primary" />
 * </mee-stack>
 * ```
 */
@Component({
  selector: 'mee-stack',
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
export class MeeStackComponent {
  /** Stack direction. Default: 'vertical'. */
  readonly direction = input<MeeStackDirection>('vertical');

  /** Gap between children. Default: 'md'. */
  readonly gap = input<MeeLayoutGap>('md');

  /** Cross-axis alignment. Default: 'stretch'. */
  readonly align = input<MeeStackAlign>('stretch');

  /** Main-axis justification. Default: 'start'. */
  readonly justify = input<MeeStackJustify>('start');

  /** Whether children wrap when the stack overflows. Default: false. */
  readonly wrap = input<boolean>(false);

  /** Derived Tailwind classes for the flex container. */
  readonly hostClass = computed<string>(() => {
    const dir     = DIRECTION_CLASS[this.direction()];
    const align   = ALIGN_CLASS[this.align()];
    const justify = JUSTIFY_CLASS[this.justify()];
    const wrap    = this.wrap() ? 'flex-wrap' : 'flex-nowrap';
    return `flex ${dir} ${align} ${justify} ${wrap}`;
  });

  /** Token-driven gap value applied via `[style.gap]`. */
  readonly gapValue = computed<string>(() => MEE_GAP_TOKEN[this.gap()]);
}
