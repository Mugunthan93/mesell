## project: mfe_pricing_responsive_polish (2026-06-18)

Task: Responsive polish audit for mfe-pricing PricingComponent (price calculator page).
Branch: design-figma-ui-screens (worktree)

Files modified:
  - frontend/apps/mfe-pricing/src/app/pricing.component.ts (3 template edits)
  - frontend/libs/ui-kit/input/input.component.ts (1 component decorator edit)

### Component structure

PricingComponent is a single inline-template component (no separate HTML/CSS files).
Layout: outer max-w-5xl wrapper > flex-col gap-6 lg:flex-row > [lg:w-2/5 input card] + [lg:w-3/5 breakdown card]
Mobile: single column (flex-col default).
Input section: mee-card > form > 2x mee-input + native range slider + mee-button (Calculate)
Breakdown section: mee-card > conditional P&L table with 7 rows + mee-badge + disclaimer text
Bottom: standalone div > mee-button (Save & Continue)

### Audit results

| Check | Result | Action |
|---|---|---|
| Two-column layout flex-col mobile | PASS | None |
| P&L input min-height 44px | PASS (mee-input has style="min-height:44px") | None |
| Input font-size >=16px | PASS (linter added font-size:16px to input concurrently) | None |
| P&L breakdown table 360px | PASS (w-full, no overflow risk) | None |
| Pricing summary row wraps | PASS | None |
| Action buttons 44px + full-width | PASS for height; GAP for width | FIXED — class="block" |
| Bottom spacing (tab bar) | PASS — shell covers it | None |
| Hardcoded widths | None found — PASS | None |
| Badge clipping | PASS | None |
| min-w-0 on flex columns | MISSING | FIXED |
| mee-input host display | MISSING | FIXED globally |

### Fixes applied

FIX 1: min-w-0 on both flex column children
  Before: class="lg:w-2/5" / class="lg:w-3/5"
  After:  class="min-w-0 lg:w-2/5" / class="min-w-0 lg:w-3/5"
  RULE: all flex children with fractional widths need min-w-0 (prevents auto min-width overflow).

FIX 2: class="block" on full-width mee-button elements
  mee-button custom element host defaults to inline-flex (PrimeNG default).
  With [fullWidth]="true" → PrimeNG p-button sets inner width:100%, but 100% of inline host ≠ 100% of parent.
  Fix: class="block" on the mee-button element forces host to display:block → inner p-button correctly fills parent.
  Applied to: Calculate button + Save & Continue button.
  NOT applied globally to MeeButtonComponent because page-header CTA button uses mee-button in inline flex row.

FIX 3: :host { display: block } on MeeInputComponent (global)
  MeeInputComponent had no host display rule. PrimeNG InputText host defaults to inline.
  mee-input is always a block form field — no usage context requires inline.
  Fix: added styles: [':host { display: block; }'] to @Component decorator in input.component.ts.
  Effect: all MFEs using mee-input now correctly fill their flex/grid parent width.

### BOTTOM SPACING RULE (re-confirmed)

Shell .page-content provides padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px)) at <=639px.
Individual MFE page wrappers must NOT add pb-[60px] or pb-[76px] — creates double gap (120px dead space).
This rule was established in dashboard audit and re-confirmed in export audit.
Pricing page: NO per-component bottom padding added.

### Cross-MFE action items
  - mfe-quality: audit for same min-w-0 + class="block" on full-width buttons
  - mee-textarea, mee-password-input: add :host { display: block } (same as mee-input fix)
  - catalog-list + preview: these have pb-[76px] from an earlier session before this rule was codified
    — those should be cleaned up in a future session to avoid double-gap

### tsc result
tsc --noEmit --project apps/mfe-pricing/tsconfig.app.json: ZERO errors.

---
