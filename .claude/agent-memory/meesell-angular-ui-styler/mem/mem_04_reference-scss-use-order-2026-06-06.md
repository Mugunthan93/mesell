## reference: scss_use_order (2026-06-06)

LEARNING: In SCSS, `@use` rules MUST precede ALL other rules.
A `@import url()` CSS import that appears before a `@use` will cause:
  `@use rules must be written before any other rules.`
Fix: Place all @use statements first, THEN @import url() CSS imports.

---
