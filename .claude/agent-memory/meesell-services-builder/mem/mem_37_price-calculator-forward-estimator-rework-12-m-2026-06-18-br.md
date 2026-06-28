## Price Calculator forward-estimator rework §12.M (2026-06-18, branch fix/pricing-engine-rework, PR #285, worktree /private/tmp/mesell-wt/pricing-rework off origin/develop@da588f3)

### Scope (founder-ratified rework + 2 locked-doc amendments + §2.D matrix edit)
Pricing flipped from BACK-SOLVE (enter MRP + target_margin → derive MRP) to FORWARD (enter
meesho_price → estimate net payout). Profit/margin are OUTPUTS; target_margin_pct REMOVED.
Commission is now a SELLER INPUT (default 4%), NOT category.get_commission — so the entire
pricing→category cross-module edge is RETIRED (§2.D 8 ✓ → 7 ✓), CommissionMissingError DELETED,
the 422 path gone. Negative payout = 200-WITH-ALERT, never 400/422.

### The estimator (service._estimate_payout, pure Decimal ROUND_HALF_EVEN via _q)
referral=price×commission%; shipping=bracketed flat; fee_base=referral+shipping+logistics+fixed;
gst_on_fees=fee_base×18% (GST on FEES not MRP); tcs=price×1%; tds=price×0%;
rto_expected_loss=return_rate%×(shipping+logistics); estimated_payout=price−Σdeductions;
profit=payout−cost; margin_pct=profit/price; markup_pct=profit/cost (both 0-guard on zero denom).
WDRP: wdrp_price=price−WDRP_DELTA, re-run estimator on it for estimated_payout_wdrp.

### CALIBRATION (the law — ₹106 → ₹47 real scraped settlement sample)
Constants that pass TOLERANCE=3.00: SHIPPING_FLAT=30 (low band price≤1000), SHIPPING_HIGH=70
(price>1000), SHIPPING_BRACKET=1000, DEFAULT_LOGISTICS_FEE=10, DEFAULT_FIXED_FEE=5,
DEFAULT_COMMISSION_PCT=4, DEFAULT_GST_PCT=18, DEFAULT_TCS_PCT=1, DEFAULT_TDS_PCT=0, WDRP_DELTA=20.
Result: estimate(106)=46.84 (residual −0.16); WDRP 86→27.98 (residual +0.98). NOTE the spec said
"SHIPPING_FLAT=70 bracketed" but 70 on a ₹106 item crushes payout to ~17 — so I made 70 the HIGH
band and 30 the calibration low band (documented in the constant docstrings + PR). Algebra to
hit a target payout: deductions = 6.0632 + 1.18×(shipping+logistics+fixed) at price 106 (the
1.18 = 1 + gst 18%; the 6.0632 = referral 4.24 + tcs 1.06 + gst-on-referral 0.7632).

### HARD RULE §12.M (6) — grep-clean gate
transfer_price / fetch-supplier-products / supplier.meesho.com MUST be ZERO under backend/app/
and appear ONLY in tests/modules/pricing/test_estimator_calibration.py. GOTCHA: I first wrote
those literal tokens into service.py's HARD-RULE docstring → grep-DIRTY. Reword any app/ docstring
to NOT contain the literal tokens (say "the scraped settlement artifacts" instead). Docs/ are
fine (gate is app/-scoped).

### Additive migration b7c2e1a9d3f4 (down_rev f31c75438e61 — was the head)
12 nullable cols: estimated_payout, referral_commission, shipping_charge, logistics_fee,
fixed_fee, gst_on_fees, tcs, tds, rto_expected_loss, return_rate_pct, markup_pct, wdrp_price.
Legacy seller_price column RE-USED to store estimated_payout; legacy commission_pct RE-PURPOSED
as the seller snapshot (no DDL change to those two). upgrade+downgrade both tested.

### Test-harness gotchas (worktree has NO .venv)
- Toolchain: master tree's 3.11 venv /Users/mugunthansrinivasan/Project/mesell/backend/.venv/bin/
  python3.11 against worktree code; ruff at /opt/homebrew/bin/ruff.
- DB: conftest REQUIRES a *_test DB whose name ends "_test" AND the connecting user must OWN
  schema public (the schema-reset fixture does DROP SCHEMA public CASCADE). meesell_test was
  owned by a different role → "must be owner of schema public". FIX: as local superuser
  (mugunthansrinivasan, peer auth on :5432) CREATE DATABASE meesell_pricerework_test OWNER meesell;
  then `create extension pgcrypto`. Pass TEST_DATABASE_URL=...meesell_pricerework_test + the full
  ~20 dummy env (DATABASE_URL, VALKEY/TEST_VALKEY/CORE_TEST_VALKEY → redis://localhost:6379/15,
  JWT_SECRET, REFRESH_TOKEN_PEPPER, MSG91_*, RAZORPAY_*, GEMINI_API_KEY, GCS_* incl
  GCS_CREDENTIALS_JSON={}, LANGFUSE_*, AUDIT_PII_SALT, CORS_ALLOWED_ORIGINS). Drop the temp DBs
  after.
- E402: this repo has NO ruff config (defaults). The pricing test idiom `pytestmark = pytest.mark.X`
  BEFORE the `from app...` import trips ruff E402. Put the import FIRST, pytestmark AFTER. (The
  original files shipped with E402 because CI evidently doesn't ruff test files — but keep mine
  clean.)
- FLAKY shared-app bug (pre-existing, FIXED here): test_feature_flag.py's stub_pricing_client used
  the module-level `app` + entered app.router.lifespan_context per test. The @rate_limit/@audit_event
  decorators on the route touch the Valkey singleton EVEN on the 404 short-circuit; a singleton bound
  to a prior function-loop → "Event loop is closed" → 500 on the 2nd patch-based flag test. FIX:
  make stub_pricing_client depend on the conftest `use_live_valkey` fixture (resets+re-points the
  singletons per function). Removing lifespan_context alone did NOT fix it (the singleton, not the
  lifespan, was the loop-bound resource).

### i18n
4 pricing keys now: validation.price.invalid_input, pricing.alert.negative_payout,
pricing.alert.low_margin, pricing.alert.shipping_dominates. Removed: pricing.commission.missing,
pricing.alert.high_mrp_multiplier, pricing.alert.thin_profit. test_i18n_generic_fallback.py
parametrizes bespoke .missing keys — had to drop pricing.commission.missing from that list.

### Validation run (real output)
70 passed (tests/modules/pricing + test_pricing_full_flow + test_i18n_generic_fallback) + 3
(persistence). ruff clean. import-linter 27 kept/0 broken (removing pricing→category import is
always allowed). Contracts 8/9/10 PASS. import smoke app routes 36. PR #285 → develop (NOT merged).
