/** @type {import('tailwindcss').Config} */
// Tailwind extends design-system tokens via CSS custom property references per §5A.H
// All color values are CSS var() references — the design-system/_tokens.scss is the source of truth.

export default {
  content: [
    "./src/**/*.{ts,html,scss}",
    "./src/**/*.component.ts",
  ],
  theme: {
    extend: {
      // Semantic colors — all reference CSS custom properties from _tokens.scss
      colors: {
        primary: 'var(--mee-color-primary)',
        // Static hex fallback for Spike background — useful when CSS vars cannot
        // be inlined (e.g. Tailwind content-scan purge at build time).
        'spike-bg': '#f0f5f9',

        'on-primary': 'var(--mee-color-on-primary)',
        secondary: 'var(--mee-color-secondary)',
        'on-secondary': 'var(--mee-color-on-secondary)',
        surface: 'var(--mee-color-surface)',
        'on-surface': 'var(--mee-color-on-surface)',
        'surface-variant': 'var(--mee-color-surface-variant)',
        'on-surface-variant': 'var(--mee-color-on-surface-variant)',
        bg: 'var(--mee-color-bg)',
        'bg-elevated': 'var(--mee-color-bg-elevated)',
        error: 'var(--mee-color-error)',
        'on-error': 'var(--mee-color-on-error)',
        success: 'var(--mee-color-success)',
        'on-success': 'var(--mee-color-on-success)',
        warning: 'var(--mee-color-warning)',
        'on-warning': 'var(--mee-color-on-warning)',
        info: 'var(--mee-color-info)',
        'on-info': 'var(--mee-color-on-info)',
        outline: 'var(--mee-color-outline)',
        'outline-variant': 'var(--mee-color-outline-variant)',
      },
      // Typography — maps to design-system scale
      fontSize: {
        'mee-xs':   'var(--mee-text-xs)',
        'mee-sm':   'var(--mee-text-sm)',
        'mee-base': 'var(--mee-text-base)',
        'mee-lg':   'var(--mee-text-lg)',
        'mee-xl':   'var(--mee-text-xl)',
        'mee-2xl':  'var(--mee-text-2xl)',
        'mee-3xl':  'var(--mee-text-3xl)',
        'mee-4xl':  'var(--mee-text-4xl)',
      },
      // Box shadows — elevation tokens
      boxShadow: {
        'mee-0': 'var(--mee-elevation-0)',
        'mee-1': 'var(--mee-elevation-1)',
        'mee-2': 'var(--mee-elevation-2)',
        'mee-3': 'var(--mee-elevation-3)',
      },
      // Transitions — motion tokens
      transitionDuration: {
        micro: 'var(--mee-motion-micro)',
        standard: 'var(--mee-motion-standard)',
        large: 'var(--mee-motion-large)',
      },
      transitionTimingFunction: {
        mee: 'var(--mee-motion-easing)',
      },
      // Font family (Spike: Plus Jakarta Sans; Inter fallback)
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      // Border radius — Spike corner tokens
      borderRadius: {
        'mee-sm':   'var(--mee-radius-sm)',
        'mee-md':   'var(--mee-radius-md)',
        'mee-lg':   'var(--mee-radius-lg)',
        'mee-full': 'var(--mee-radius-full)',
      },
    },
  },
  plugins: [],
};
