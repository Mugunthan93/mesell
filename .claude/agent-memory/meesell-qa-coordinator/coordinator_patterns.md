# Coordinator patterns — cross-wave learning

Recurring gaps in what BUILDERS ship, observed at the merge gate. Each entry feeds
the next wave's spec automatically so every wave is smarter than the last. Format:
`pattern → which builder/lane → what to pre-empt in the next spec`.

## Seeded from prior project memory (2026-06-22)
- **Backend routes ship without error-path tests** → backend lane → every route in
  a spec must require ≥1 happy-path AND ≥1 error-path test.
- **Missing i18n fallback keys render blank errors** (e.g. `validation.generic.missing`,
  `validation.size_in_ltrs.invalid_enum_value`, `auth.token.missing`) → backend i18n →
  assert that a 422/validation message resolves to a non-empty string, not a raw key.
- **FE/BE contract drift surfaces as runtime 4xx** (e.g. suggest GET→POST 405;
  autofill reading `product_title` vs canonical `product_name`) → integration/E2E →
  assert the actual method + payload shape against the live OpenAPI.
- **Federation auth-singleton regression** (shell→remote nav logs the user out when
  `@mesell/core` is not deduped) → E2E → the `logout-guard` flow is the sentinel; keep it.
- **Assertion-free / `assert True` tests** slip in under time pressure → all lanes →
  reject at the gate; a test that asserts nothing is a defect.


## From Wave 1 — e2e lane (PR #385, 2026-06-22)
- **PROVISIONAL selectors written before exploration are frequently WRONG** → E2E lane →
  the registry must be LIVE-VERIFIED before codification; ~8 of the bootstrap provisional
  selectors were stale/renamed. The two-phase mandate (explore→codify) caught all of them.
  Keep enforcing: a selector that is not in `selector_registry.md` as LIVE-VERIFIED is a reject.
- **Federation singleton staleness bites the SHARED LIB, not just remotes** → E2E/frontend →
  a stale shell-hosted `@mesell/ui-kit` singleton makes `[testId]` passthroughs silently no-op
  even when the rebuilt remote bundle contains the string. Rebuilding remotes is NOT enough —
  the SHELL (singleton host) must be rebuilt too. (federation_quirks.md, Wave-1.)
- **Single-use rotating refresh token breaks shared `storageState`** → E2E auth setup →
  the standard "auth.setup saves one storageState → all flows reuse it" pattern 401s the 2nd
  flow. The robust pattern is a worker-scoped shared authed context (one login per worker).
  Bake this into every future E2E wave's auth fixture; do NOT regress to plain storageState reuse.
- **Hardcoded placeholder IDs in feature code surface only at the E2E/integration layer** →
  E2E → mfe-export shipped `productId='current-product-id'` (a unit/component test mocking the
  service would never catch it). The full-flow E2E export-download test is the only guard;
  keep flows that exercise REAL created entities (createProductViaPicker → real UUID) rather
  than stubbing the id.
