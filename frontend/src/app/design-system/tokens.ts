// design-system/tokens.ts
// TS mirror of selected runtime-readable design tokens per §3.C.3
// Used for: chart.js color rendering, Angular animations, canvas rendering
// SCSS _tokens.scss is the source of truth — update SCSS first, then this file.

/** Motion duration tokens in ms (for Angular animations + JS-driven transitions) */
export const MOTION = {
  micro: 100,
  standard: 200,
  large: 300,
} as const;

/** Semantic color tokens as CSS custom property references (for chart.js / canvas) */
export const COLORS = {
  primary: 'var(--mee-color-primary)',
  onPrimary: 'var(--mee-color-on-primary)',
  secondary: 'var(--mee-color-secondary)',
  onSecondary: 'var(--mee-color-on-secondary)',
  surface: 'var(--mee-color-surface)',
  onSurface: 'var(--mee-color-on-surface)',
  error: 'var(--mee-color-error)',
  onError: 'var(--mee-color-on-error)',
  success: 'var(--mee-color-success)',
  onSuccess: 'var(--mee-color-on-success)',
  warning: 'var(--mee-color-warning)',
  onWarning: 'var(--mee-color-on-warning)',
  info: 'var(--mee-color-info)',
  onInfo: 'var(--mee-color-on-info)',
  outline: 'var(--mee-color-outline)',
} as const;

/** Resolved hex values for chart.js (CSS custom props don't work in canvas context) */
export const COLORS_RESOLVED = {
  primary: '#F26B23',
  secondary: '#1E40AF',
  error: '#DC2626',
  success: '#16A34A',
  warning: '#D97706',
  info: '#2563EB',
  outline: '#D1D5DB',
} as const;
