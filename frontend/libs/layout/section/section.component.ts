import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MEE_GAP_TOKEN, type MeeLayoutGap } from '../layout.types';

/**
 * `mee-section` — titled content section within a page.
 *
 * Wraps a labeled sub-region (e.g. "Account details", "Recent catalogs").
 * The `<h2>` heading and optional description render only when their inputs
 * are set. The section body is always projected via `<ng-content />`.
 *
 * Styling idiom: Tailwind utilities for typography + `[style.gap]` binding
 * to `var(--mee-space-N)` tokens for vertical rhythm between header and body.
 *
 * @example
 * ```html
 * <mee-section heading="Recent catalogs" description="Your last 20 listings">
 *   <mee-grid>...</mee-grid>
 * </mee-section>
 * ```
 */
@Component({
  selector: 'mee-section',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (hasHeader()) {
      <div class="flex flex-col gap-1 mb-1">
        @if (heading()) {
          <h2
            class="text-lg font-semibold leading-snug"
            style="color: var(--mee-color-on-surface);"
          >{{ heading() }}</h2>
        }
        @if (description()) {
          <p
            class="text-sm"
            style="color: var(--mee-color-on-surface-muted);"
          >{{ description() }}</p>
        }
      </div>
    }
    <div [style.margin-top]="hasHeader() ? gapValue() : '0'">
      <ng-content />
    </div>
  `,
  styles: [`:host { display: block; }`],
})
export class MeeSectionComponent {
  /** Section heading — renders an `<h2>` only when set. */
  readonly heading = input<string | undefined>(undefined);

  /** Optional paragraph under the heading. */
  readonly description = input<string | undefined>(undefined);

  /** Vertical gap between the header block and the projected body. Default: 'md'. */
  readonly gap = input<MeeLayoutGap>('md');

  /** True when at least heading or description is provided. */
  readonly hasHeader = computed<boolean>(
    () => !!this.heading() || !!this.description()
  );

  /** Token-driven gap value for the header-to-body spacing. */
  readonly gapValue = computed<string>(() => MEE_GAP_TOKEN[this.gap()]);
}
