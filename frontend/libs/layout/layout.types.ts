/**
 * @mesell/layout — shared layout types.
 *
 * `MeeLayoutGap` is the single spacing scale consumed by every layout primitive.
 * It maps to the design-token spacing system so no hard-coded px values appear
 * in the primitives' computed style bindings.
 *
 * Gap scale (4px base):
 *   none → 0
 *   xs   → var(--mee-space-1)  =  4px
 *   sm   → var(--mee-space-2)  =  8px
 *   md   → var(--mee-space-4)  = 16px
 *   lg   → var(--mee-space-6)  = 24px
 *   xl   → var(--mee-space-8)  = 32px
 */
export type MeeLayoutGap = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';

/** Map from `MeeLayoutGap` → CSS value (token var or 0). */
export const MEE_GAP_TOKEN: Record<MeeLayoutGap, string> = {
  none: '0',
  xs:   'var(--mee-space-1)',
  sm:   'var(--mee-space-2)',
  md:   'var(--mee-space-4)',
  lg:   'var(--mee-space-6)',
  xl:   'var(--mee-space-8)',
};

/** Max-width options for page/form containers. */
export type MeePageMaxWidth = 'sm' | 'md' | 'lg' | 'xl' | 'full';

/** Max-width options for form columns (tighter set). */
export type MeeFormMaxWidth = 'sm' | 'md' | 'lg' | 'full';

/**
 * Discrete horizontal/vertical padding scale for `mee-page`.
 *   'none'    → no padding (edge-to-edge); equivalent to the boolean `false`.
 *   'tight'   → 'px-4 py-6 sm:px-6'           (omits the lg:px-8 step — for
 *               pixel-parity adoption by pages that hand-roll this padding).
 *   'default' → 'px-4 py-6 sm:px-6 lg:px-8'   (the design-system standard;
 *               equivalent to the boolean `true`).
 *
 * `mee-page`'s `padding` input accepts `boolean | MeePagePadding` for backward
 * compatibility: `false ≡ 'none'`, `true ≡ 'default'`.
 */
export type MeePagePadding = 'none' | 'tight' | 'default';
