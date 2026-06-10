// meesell-preset.ts
// Defines MeeSell's PrimeNG theme by extending Aura with brand tokens.
// This is the ONLY place PrimeNG theme configuration lives.

import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

export const MeeSellPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#fff3ec',
      100: '#ffddc4',
      200: '#ffbd94',
      300: '#ff9b60',
      400: '#ff8040',
      500: '#F26B23',   // MeeSell orange
      600: '#d45a18',
      700: '#b04a10',
      800: '#8c3b0b',
      900: '#6e2e07',
      950: '#4a1d03',
    },
    colorScheme: {
      light: {
        surface: {
          0:   '#ffffff',
          50:  '#f0f5f9',
          100: '#e8eef4',
          200: '#dde5ef',
          300: '#cdd7e5',
          400: '#b0bdd0',
          500: '#8a9ab5',
          600: '#6b7fa0',
          700: '#506080',
          800: '#384463',
          900: '#2a3547',
          950: '#1a2338',
        },
        primary: {
          color:           '#F26B23',
          contrastColor:   '#ffffff',
          hoverColor:      '#d45a18',
          activeColor:     '#b04a10',
        },
        highlight: {
          background:      'rgba(242, 107, 35, 0.12)',
          focusBackground: 'rgba(242, 107, 35, 0.20)',
          color:           '#F26B23',
          focusColor:      '#d45a18',
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
