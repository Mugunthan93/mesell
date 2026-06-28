## Session: pricing-fe-rework slice 1 (2026-06-18)

**Branch/commit:** feat/pricing-fe-rework @ eca463e
**PR:** #287 (→ develop, open — do NOT merge, slices 2+3 follow)
**Worktree:** /private/tmp/mesell-wt/pricing-fe-rework

### Contract confirmed (backend fd4331d / PR #285 §12.M)

PriceCalcRequest: meesho_price (primary), input_cost, commission_pct (default "4"),
  return_rate_pct (default "0"), mrp (optional), override_shipping, override_logistics_fee,
  override_fixed_fee, override_gst_pct, override_tcs_pct, override_tds_pct.
  DEAD: target_margin_pct.

PriceCalcResponse: mrp (nullable), meesho_price, wdrp_price, input_cost, commission_pct,
  referral_commission, shipping_charge, logistics_fee, fixed_fee, gst_pct, gst_on_fees,
  tcs, tds, return_rate_pct, rto_expected_loss, total_deductions, estimated_payout,
  estimated_payout_wdrp, profit, margin_pct, markup_pct, alerts[], calculated_at.
  DEAD: seller_price, commission_amount, gst_amount, profit_pct.

Alert codes: NEGATIVE_PAYOUT | LOW_MARGIN | SHIPPING_DOMINATES.
  DEAD: HIGH_MRP_MULTIPLIER, THIN_PROFIT.
ALERT_MESSAGES keys: pricing.alert.negative_payout / .low_margin / .shipping_dominates.
422 path: DEAD (§12.M (4)). PriceCalcCommissionMissingError DELETED.

### Key learnings

**Forward estimator contract shift:** §12.E was backward (input_cost+target_margin → mrp output).
  §12.M is forward (meesho_price input → estimated_payout output). Model contracts are INVERSE.
  component forms must be rebuilt top-to-bottom for this flip.

**Pre-existing TS errors block ng test on origin/develop:** The worktree off origin/develop
  has pre-existing TS errors in mfe-auth (errorMessage signal), mfe-onboarding, shell specs.
  These errors are from modified working-tree files (shown in git status) that haven't been
  pushed to origin. Pure-function pricing specs still run via bare vitest run.
  Service specs (with @mesell/core) require ng test runner for tsconfig path resolution.
  Strategy: confirm 0 mfe-pricing errors via tsc --noEmit + run component spec via vitest.

**pricing.component.spec.ts must be updated in slice 1, not slice 2:**
  The component spec imports model types directly. Removing PriceCalcCommissionMissingError
  from the model breaks the spec compile immediately — must fix in the same slice as the model.
  Pattern: always update the spec that imports the model IMMEDIATELY when the model changes.

**TODO(slice-2) casting pattern for dead switch cases:**
  When a union case is removed from a type (commission_missing deleted from PriceCalcErrorShape),
  TypeScript raises an error on any switch case that matches it. Temporary fix until slice 2:
  cast the dead case label: `case 'commission_missing' as 'validation':`. This compiles but
  is clearly marked for deletion. Do not leave this in for longer than one slice.

**vitest vs ng test resolution:** bare `vitest run <file>` resolves relative + rxjs imports
  but NOT tsconfig path aliases (@mesell/*). ng test resolves everything via tsconfig.
  For specs that only import from local files + standard libs: use bare vitest.
  For specs that import @mesell/core ApiClient: must use ng test (fails when suite-wide TS errors block build).
