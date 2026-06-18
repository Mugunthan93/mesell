# Merge-gate review: PR #282 — Postman collection tooling (2026-06-18)

**Verdict: APPROVE-FOR-FOUNDER.** Founder owns the `chore/postman-collection → develop` merge (D1). I did NOT merge.

PR #282: hand-authored Postman v2.1 collection + env + regen scripts. Branch `chore/postman-collection`, single commit `36fe8c3` on top of `origin/develop` (`b28ef2f`). +4872/-0.

## Checklist results (all PASS)
1. Zero app-code: authoritative diff `origin/develop..FETCH_HEAD` = only `backend/postman/**` (4) + `backend/scripts/**` (2). No `backend/app/**`, no requirements.txt. PASS.
2. Collection valid v2.1 (schema `...v2.1.0/collection.json`), 31 requests, 9 folders (Auth, Seller Profile, Categories, Products, Images, Pricing, Exports, Webhooks, Health). PASS.
3. Collection-level Bearer `{{access_token}}`; all requests use `{{base_url}}`; exactly 5 noauth = otp/send, otp/verify, refresh, webhooks/razorpay, health. PASS. (Note: `base_url` lives in the env file, not collection vars — fine.)
4. SECURITY: env ships all secret vars EMPTY. No `eyJ` JWTs, no real keys. Only hits = sentinel placeholders in gen_openapi.py (`dev-msg91-auth-key-sentinel` etc.) + openapi.json schema property names. PASS.
5. OTP-verify test script extracts `access_token` from 200 body and `pm.environment.set('access_token', ...)`. PASS.
6. Reproducible: gen_openapi.py (stdlib urllib, in-process dump with 18-var §5.D sentinel injection, graceful fallback to live :8000) + gen_postman.sh (`set -euo pipefail`, venv+worktree resolution, npx `--yes`). README documents regen command + the in-process-vs-live fallback caveat honestly. PASS.
7. No new dep in requirements.txt; converter via `npx --yes` only. PASS.
8. PR template fully filled, no `<>`, migration N/A. PASS.

Coverage cross-check: all 30 spec operations (25 paths) present in collection 1:1; 31st request is the Login-dev OTP split. openapi.json = 25 paths / 30 ops / OpenAPI 3.1.0.

## Minor doc nit (non-blocking, flagged in report)
README "Regeneration" step 3 says script writes `meesell.postman_collection.json`, but gen_postman.sh actually writes `meesell_generated.postman_collection.json` (intentional — preserves the hand-authored primary; script header explains this). Cosmetic inconsistency between README prose and script. Founder may ask builder to align wording in a follow-up; not a gate failure.

## Gotcha for future reviews
Local `develop` was stale at `b6bda89` while `origin/develop` was `b28ef2f`. A `git diff localdevelop...FETCH_HEAD` falsely showed ~35 unrelated files (i18n, frontend, docs). ALWAYS diff against `origin/develop` (fetch first) and confirm `git log origin/develop..FETCH_HEAD` shows only the expected PR commits before judging scope.
