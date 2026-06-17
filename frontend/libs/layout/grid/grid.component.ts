import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MEE_GAP_TOKEN, type MeeLayoutGap } from '../layout.types';

/** Column count options for `mee-grid`. 'auto' uses auto-fill. */
export type MeeGridCols = 'auto' | 1 | 2 | 3 | 4;

/**
 * Tailwind grid-cols classes for numeric `cols` values.
 *
 * Mobile-first (Tirupur sellers on 360–414px phones — CLAUDE §audience):
 *   base    → 1 column (all phones)
 *   sm:640  → 2 columns (large phones / small tablets)
 *   md:768  → 3 columns (tablets) — for cols=3 and cols=4 only
 *   lg:1024 → 4 columns (desktops) — for cols=4 only
 *
 * cols=4: was `sm:2 → md:4` — the jump from 2 to 4 at 768px is abrupt on
 * tablets. Fixed to `sm:2 → md:3 → lg:4` so tablet users get 3 columns
 * at 768–1023px, and only desktop (1024px+) expands to the full 4 columns.
 */
const COLS_CLASS: Record<1 | 2 | 3 | 4, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3',
  4: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4',
};

/**
 * `mee-grid` — responsive 2-D grid for card/tile layouts.
 *
 * `cols='auto'` uses `repeat(auto-fill, minmax(<minItemWidth>, 1fr))` so the
 * browser fills as many columns as fit — no fixed breakpoints needed.
 * Numeric `cols` values collapse to 1 column on mobile (Tirupur sellers).
 *
 * Styling idiom: Tailwind `grid grid-cols-*` classes for numeric cols +
 * `[style.grid-template-columns]` computed style for `auto` mode +
 * `[style.gap]` binding to `var(--mee-space-N)` tokens.
 *
 * @example
 * ```html
 * <!-- Auto-fill tiles, at least 16rem wide each -->
 * <mee-grid cols="auto" minItemWidth="16rem" gap="md">
 *   <mee-catalog-card *ngFor="let c of catalogs" [catalog]="c" />
 * </mee-grid>
 *
 * <!-- Fixed 3 columns at md+, 1 column on mobile -->
 * <mee-grid [cols]="3" gap="md">...</mee-grid>
 * ```
 */
@Component({
  selector: 'mee-grid',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      [class]="hostClass()"
      [style.grid-template-columns]="gridTemplateColumns()"
      [style.gap]="gapValue()"
    >
      <ng-content />
    </div>
  `,
  styles: [`:host { display: block; }`],
})
export class MeeGridComponent {
  /**
   * 'auto' → auto-fill responsive grid (uses `minItemWidth`).
   * 1|2|3|4 → fixed column count at sm/md, collapses to 1 on mobile.
   * Default: 'auto'.
   */
  readonly cols = input<MeeGridCols>('auto');

  /**
   * Minimum item width used when `cols='auto'`.
   * Default: '16rem'.
   */
  readonly minItemWidth = input<string>('16rem');

  /** Grid gap (applied to both row and column gap). Default: 'md'. */
  readonly gap = input<MeeLayoutGap>('md');

  /** Tailwind classes for the grid container. */
  readonly hostClass = computed<string>(() => {
    const c = this.cols();
    if (c === 'auto') {
      return 'grid';
    }
    return `grid ${COLS_CLASS[c]}`;
  });

  /**
   * `grid-template-columns` style — set only in auto mode; null for numeric
   * cols (Tailwind handles those via class).
   */
  readonly gridTemplateColumns = computed<string | null>(() => {
    if (this.cols() === 'auto') {
      return `repeat(auto-fill, minmax(${this.minItemWidth()}, 1fr))`;
    }
    return null;
  });

  /** Token-driven gap value applied via `[style.gap]`. */
  readonly gapValue = computed<string>(() => MEE_GAP_TOKEN[this.gap()]);
}
