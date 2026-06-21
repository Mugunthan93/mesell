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
