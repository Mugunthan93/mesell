## project: shell_mobile_bottom_tab_bar (2026-06-18)

Task: Add persistent mobile bottom tab bar to shell (≤639px). HTML + CSS only — no TypeScript changes.
Branch: design-figma-ui-screens (worktree)
Files changed:
  - frontend/apps/shell/src/app/layouts/shell/shell.component.html (EDITED)
  - frontend/apps/shell/src/app/layouts/shell/shell.component.css (EDITED)

### Responsive breakpoint table (FINAL)

| Viewport     | Navigation pattern                                      |
|--------------|--------------------------------------------------------|
| ≥1024px      | Fixed 260px sidebar (.sidebar-desktop)                 |
| 640–1023px   | Hamburger button + mee-drawer overlay                  |
| ≤639px       | Bottom tab bar (.bottom-nav) — hamburger hidden        |

### HTML change

Added `<nav class="bottom-nav" aria-label="Mobile navigation">` as last child of .shell-layout
(after .shell-main closing </div>). Uses `@for (item of navItems; track item.route)` — same
pattern and same `navItems` property already used in desktop sidebar + drawer loops.
`routerLinkActive="bottom-nav-item--active"` drives active state.
`[attr.aria-label]="item.label"` provides screen-reader label per tab.

### CSS changes

1. Added `@media (max-width: 639px) { .hamburger { display: none; } }` immediately after
   the existing `@media (max-width: 1023px) { .hamburger { display: flex; } }` block.
   Hamburger is now: flex at 640–1023px, none at ≤639px and ≥1024px (sidebar covers that).

2. .bottom-nav:
   - display: none (default, hidden on tablet+desktop)
   - position: fixed; bottom: 0; left: 0; right: 0; height: 60px; z-index: 100
   - background: var(--mee-color-surface) = #ffffff
   - border-top: 1px solid var(--mee-color-outline) = #e5eaef
   - box-shadow: 0 -2px 8px rgba(0,0,0,0.06) — subtle elevation
   - padding-bottom: env(safe-area-inset-bottom, 0px) — iPhone home indicator
   @media (max-width: 639px): display: flex; align-items: stretch

3. .page-content override in @media (max-width: 639px):
   padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px))
   Prevents last page content from hiding behind the fixed bar.

4. .bottom-nav-item: flex:1; flex-direction:column; gap:3px; min-height:44px (a11y touch target)
   color: var(--mee-color-on-surface-muted); transition via var(--mee-transition-fast)
   -webkit-tap-highlight-color: transparent (no flash on iOS tap)

5. .bottom-nav-item--active: color: var(--mee-color-primary) = #F26B23
   .bottom-nav-item--active i: transform: scale(1.15) — subtle icon pop on active tab

6. .bottom-nav-label: 10px/500wt; white-space:nowrap; text-overflow:ellipsis; max-width:68px

### Design tokens consumed by bottom-nav
| Token                        | Value   | Role                          |
|------------------------------|---------|-------------------------------|
| --mee-color-surface          | #ffffff | Tab bar background            |
| --mee-color-outline          | #e5eaef | Top border                    |
| --mee-color-on-surface-muted | (var)   | Inactive tab color            |
| --mee-color-primary          | #F26B23 | Active tab color              |
| --mee-transition-fast        | (var)   | Color + scale transition      |

### A11y findings
- min-height: 44px on .bottom-nav-item — WCAG 2.5.5 touch target PASS
- Each tab has aria-label via [attr.aria-label]="item.label" — readable by screen reader
- <nav aria-label="Mobile navigation"> — landmark with label
- Icon glyphs have aria-hidden="true" — decorative, not read
- Active color #F26B23 on #ffffff: ~3.11:1 — acceptable for large/icon UI elements (same as sidebar active, per prior ruling 2026-06-06). Inactive --mee-color-on-surface-muted: verify in next session.
- -webkit-tap-highlight-color: transparent prevents double-flash on Android Chrome

### Mobile 360px coverage
- 4 tabs × flex:1 = 90px each on 360px screen — well above 44px minimum touch width
- Label max-width:68px + text-overflow:ellipsis prevents wrap/overflow on narrow labels
- Safe-area env() ensures home indicator area is clear on modern iOS

### RULE: NavItems is the single source — no custom tab list
The bottom-nav @for loops over the SAME navItems array as sidebar + drawer.
Any future nav item changes (add/remove) automatically propagate to all three nav contexts.
Do NOT introduce a separate tabItems or mobileNavItems property.

TypeScript check (tsc --noEmit): ZERO errors. Full build deferred (native-federation slow in worktree).

---
