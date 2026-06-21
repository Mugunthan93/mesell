# MeeSell Review Gates (advisory — HYBRID dispatch step 3)

> **How:** the owning coordinator runs the BUILT-IN `/code-review` (and `/security-review`
> for security-sensitive diffs) on the specialist's `feature/{slug}/{group}` PR, applying
> the MeeSell checklists below. Findings are recorded on the discipline's status board /
> coordinator memory — never left in throwaway chat. These gates are ADVISORY / non-blocking
> for now; the coordinator may still reject back to the specialist. Promote `/code-review`
> to a REQUIRED develop context after ~10 clean PRs. See `docs/dev/CLAUDE_FEATURE_ADOPTION.md`
> for the adoption plan.

## `/code-review` checklist (MeeSell bug classes)

- **Federation:** every shared `@mesell/*` lib has `singleton: true` plus a consistent
  `version` pin (`MESELL_SHARED_VERSION`); no `mesellShared` drift across the 8 federation
  configs; `mfe-billing` carries the pin. (Prevents the shell -> remote singleton-logout class.)
- **FE <-> BE contract parity:** HTTP verb (GET vs POST), field names, and enum values match
  between the Angular service call and the FastAPI route / schema. (This class caused the
  suggest-405, autofill `product_name`, and `size_in_ltrs` 422 bugs.)
- **Auth / session:** in-memory access token + authGuard logout risks; refresh handling.
- **Flag-gating:** Razorpay-live and held-google-auth changes are feature-flag gated.
- **Constraints:** no committed creds / secrets; READ-ONLY scraping; zero-spend posture;
  never-go-live.
- **Standard:** correctness bugs, error handling, `user_id` / tenant scoping.

## `/security-review` checklist (diff-scoped; EXCLUDE `.env`, `*.example`, secrets, `.venv`)

- `user_id` repository / tenant scoping on every query.
- JWT in-memory + refresh token in HttpOnly / Secure / SameSite=Strict cookie + Valkey revocation.
- Razorpay webhook signature verification.
- GCS signed-URL TTL bounds.
- READ-ONLY scraper egress only.
- Injection (SQL / command) + authz on every endpoint.

Fixes route to a `meesell-*` specialist — never applied by the review skill itself.

## When to run which

- **`/code-review`:** EVERY group / integration PR.
- **`/security-review`:** additionally on diffs touching auth, billing / Razorpay, or the scraper.
