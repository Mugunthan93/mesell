## reference: theme_import (2026-06-06)

CRITICAL: `_theme.scss` was scaffolded by the service-builder but was NEVER imported
into `styles.scss`. Angular Material M3 CSS custom properties were never emitted.
Fix: Added `@use 'app/design-system/theme';` to `styles.scss` after `@use 'app/design-system/tokens'`.
This is a load-bearing import — without it, all Material theming is inactive.

---
