// design-system/breakpoints.ts
// TS mirror of SCSS breakpoint tokens per §3.C.3 + §5A.E
// Used for: JS-driven layout decisions, lazy module triggers, virtual-scroll item heights
// SCSS is the source of truth — update _tokens.scss first, then this file.

export const BREAKPOINTS = {
  /** 360px baseline — every component designed here first (Tirupur low-end Android) */
  xs: 0,
  /** 640px — larger phones, small tablets */
  sm: 640,
  /** 768px — tablets portrait */
  md: 768,
  /** 1024px — tablets landscape, small laptops */
  lg: 1024,
  /** 1280px — desktops */
  xl: 1280,
} as const;

export type BreakpointKey = keyof typeof BREAKPOINTS;
