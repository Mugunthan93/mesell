import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MEE_GAP_TOKEN, type MeeLayoutGap, type MeePageMaxWidth, type MeePagePadding } from '../layout.types';

/** Tailwind max-width class map for `mee-page`. */
const MAX_WIDTH_CLASS: Record<MeePageMaxWidth, string> = {
  sm:   'max-w-screen-sm',
  md:   'max-w-screen-md',
  lg:   'max-w-screen-lg',
  xl:   'max-w-screen-xl',
  full: 'max-w-none',
};

/**
 * `mee-page` — top-level routed-page container.
 *
 * Centers content at a responsive max-width, applies horizontal/vertical
 * padding, and provides vertical rhythm between projected child sections
 * via a token-driven gap.
 *
 * Styling idiom: Tailwind classes for max-width/centering + `[style.gap]`
 * binding to `var(--mee-space-N)` tokens for the gap (token map in
 * `MEE_GAP_TOKEN`). This keeps gap values out of Tailwind's JIT scan and
 * tied to the design-token source-of-truth.
 *
 * A11y landmark decision (Phase 3, 2026-06-17):
 * `mee-page` renders a `<div>`, NOT `<main>`. The Phase-4 shell's template
 * already wraps `<router-outlet>` inside a `<main class="page-content">`.
 * Rendering a second `<main>` inside `mee-page` would produce a nested/duplicate
 * main landmark — a WCAG 2.4.1 violation (screen readers announce it twice).
 * The correct ownership is: shell owns `<main>`, mee-page owns the content
 * column layout within it. If the Phase-4 shell or auth flow ever removes its
 * own `<main>`, mee-page can be updated to render one. Flagged to coordinator.
 *
 * @example
 * ```html
 * <mee-page maxWidth="lg" [padding]="true" gap="lg">
 *   <mee-section heading="Recent catalogs">...</mee-section>
 * </mee-page>
 * ```
 */
@Component({
  selector: 'mee-page',
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
export class MeePageComponent {
  /** Max readable width of the page content column. Default: 'lg'. */
  readonly maxWidth = input<MeePageMaxWidth>('lg');

  /**
   * Page padding. Accepts a boolean (back-compat) or the `MeePagePadding`
   * scale:
   *   false / 'none'    → no padding (edge-to-edge)
   *   'tight'           → 'px-4 py-6 sm:px-6'           (no lg:px-8 step)
   *   true  / 'default' → 'px-4 py-6 sm:px-6 lg:px-8'   (design-system default)
   * Default is `true` (≡ 'default') — unchanged from before.
   */
  readonly padding = input<boolean | MeePagePadding>(true);

  /** Vertical gap between projected child blocks. Default: 'lg'. */
  readonly gap = input<MeeLayoutGap>('lg');

  /** Resolve the boolean | MeePagePadding input → Tailwind padding class string. */
  private readonly paddingClass = computed<string>(() => {
    const p = this.padding();
    // Boolean back-compat: true ≡ 'default', false ≡ 'none'. Handle boolean first.
    if (p === false || p === 'none') return '';
    if (p === 'tight') return 'px-4 py-6 sm:px-6';
    // p === true || p === 'default'
    return 'px-4 py-6 sm:px-6 lg:px-8';
  });

  /** Derived Tailwind classes applied to the inner `<div>` wrapper. */
  readonly hostClass = computed<string>(() => {
    const mw = MAX_WIDTH_CLASS[this.maxWidth()];
    const pad = this.paddingClass();
    return `flex flex-col w-full mx-auto ${mw} ${pad}`.trim();
  });

  /** Token-driven gap value applied via `[style.gap]`. */
  readonly gapValue = computed<string>(() => MEE_GAP_TOKEN[this.gap()]);
}
