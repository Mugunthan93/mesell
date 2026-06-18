// theme.alt.ts
// Alternate MeeSell theme preset — green brand (#2E7D32, Material Green 800).
// Intended as a demo / swap candidate. Live defaults remain in theme.ts (orange).
//
// SWAP NOTE: to activate this theme, change providers.ts:
//   preset: MeeSellPreset  →  preset: MeeSellAltPreset
// (and update the import). See SWAP_GUIDE.md for the full procedure.
//
// This file MUST NOT import from theme.ts — it is a fully independent preset.

import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

export const MeeSellAltPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#e8f5e9',
      100: '#c8e6c9',
      200: '#a5d6a7',
      300: '#81c784',
      400: '#66bb6a',
      500: '#4caf50',   // Material Green 500
      600: '#43a047',
      700: '#388e3c',
      800: '#2E7D32',   // MeeSell Alt green (brand anchor)
      900: '#1b5e20',
      950: '#0d3d12',
    },
    colorScheme: {
      light: {
        surface: {
          0:   '#ffffff',
          50:  '#f1f8f1',
          100: '#e8f3e8',
          200: '#daeeda',
          300: '#c6e5c6',
          400: '#a5cfa5',
          500: '#80b380',
          600: '#5f9c5f',
          700: '#447a44',
          800: '#2f5c2f',
          900: '#1e3e1e',
          950: '#102710',
        },
        primary: {
          color:           '#2E7D32',
          contrastColor:   '#ffffff',
          hoverColor:      '#256428',
          activeColor:     '#1b5e20',
        },
        highlight: {
          background:      'rgba(46, 125, 50, 0.12)',
          focusBackground: 'rgba(46, 125, 50, 0.20)',
          color:           '#2E7D32',
          focusColor:      '#256428',
        },
      },
    },
  },
  components: {
    card: {
      root: {
        borderRadius: '16px',
        shadow:       '0 4px 12px rgba(0,0,0,0.08)',
      },
    },
    button: {
      root: {
        borderRadius: '999px',
        paddingX:     '1.25rem',
      },
    },
    inputtext: {
      root: {
        borderRadius: '7px',
      },
    },
    select: {
      root: {
        borderRadius: '7px',
      },
    },
    dialog: {
      root: {
        borderRadius: '16px',
      },
    },
    panel: {
      root: {
        borderRadius: '16px',
      },
    },
  },
});
