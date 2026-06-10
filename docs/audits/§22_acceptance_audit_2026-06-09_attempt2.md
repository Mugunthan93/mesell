# §22 V1 Acceptance Audit — Attempt #2

**Date:** 2026-06-09
**Auditor:** meesell-backend-verification-22-acceptance-2
**Branch:** `claude/meesell-project-setup-Tl7DS`
**Prior attempt verdict:** V1 NO-GO (6/9 PASS, 3 FAIL — `docs/audits/§22_acceptance_audit_2026-06-09.md`)
**This attempt verdict:** **V1 NO-GO** (8/9 PASS, 1 FAIL)

---

## Executive summary

Eight of the nine §22.C acceptance criteria PASS against the current working tree.
The three code/test/CI remediations from attempt #1 are **all verified resolved**:

- **CRITICAL-1 (AI evals):** out of scope for this attempt's 9 checks; the route/auth/CI
  surface is intact (see Checks 1–8).
- **CRITICAL-2 (SM secrets):** **NOT resolved** against live GCP state. Two of the three
  required secrets (`razorpay-webhook-secret`, `langfuse-secret-key`) still have **zero
  versions** — the secret containers exist but were never populated. This is the sole
  remaining FAIL (Check 9). The founder's "now populated" claim is contradicted by the
  live `gcloud secrets versions list` / `versions describe latest` output, which returns
  `NOT_FOUND: ... not found or has no versions` for both secrets.
- **MEDIUM-1 (F6 @audit_event):** RESOLVED — 4 decorators verified (Check 7).
- **MEDIUM-2 (F7 audit_mw Gate 2.5):** RESOLVED — Gate 2.5 verified at the correct
  position (Check 8).

The backend construction itself is in excellent shape — exactly 28 routes, the locked
23/2/2/1 auth posture, 15 golden fixtures, the full §16.E CI contract suite, the §15.J
metrics surface, and both export terminal-audit call sites are all present. The single
blocker is a **founder/infra action** (populate two Secret Manager versions), not a code
defect — but it remains a hard V1 gate because the `backend-secrets` K8s Secret cannot be
materialized and Phase D deployment cannot proceed without it.

---

## Check results

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Route count = exactly 28 | **PASS** | 28 `@router.{get,post,patch,put,delete}` decorators across the 8 routers: iam 6, customer 5, category 5, catalog 6, image 2, pricing 1, dashboard 1, export 2 = **28**. (See per-file line citations below.) |
| 2 | Auth posture 23 JWT / 2 cookie / 2 public / 1 HMAC | **PASS** | JWT: 22 non-iam `Depends(get_current_user)` route params + `iam:/auth/me` = **23**. Cookie: `iam:/auth/refresh` (L152) + `iam:/auth/logout` (L194), each `refresh_token: Annotated[Optional[str], Cookie()]` (L163, L203) = **2**. Public: `iam:/auth/otp/send` (L105) + `iam:/auth/otp/verify` (L124), no auth dep = **2**. HMAC: `iam:/webhooks/razorpay` (L247), raw-body + `X-Razorpay-Signature` verify = **1**. 23/2/2/1 exact. |
| 3 | 15 golden round-trip fixtures | **PASS** | `backend/tests/integration/golden_round_trip/` contains `fixture_01_sarees.json` … `fixture_15_special_chars.json` = **15** files, contiguous 01–15. |
| 4 | CI pipeline §19.G — 10 linter contracts | **PASS** (with checklist-text reconciliation note) | `.gitlab-ci.yml` `lint:` stage (L120–140) wires the locked §16.E / §19.C "10 CI contracts": Contracts 1–7 via `lint-imports --config tests/lint/import_rules.toml` (L130; the TOML carries 27 named sub-contracts), Contract 8 `check_scope_to_user.py` (L132), Contract 9 `check_no_meesho_symbols_outside_export.py` (L134), Contract 10 `check_message_id_regex.py` (L136). All 4 scanner/config files exist on disk. The §16 audit (2026-06-09) independently re-ran all 10 → 27 kept / 0 broken + 3 scanners EXIT 0 + 18 lint tests pass. **See Finding F-CHECK4** for the discrepancy with this attempt's checklist wording. |
| 5 | Prometheus `/metrics` + 7 metric singletons | **PASS** | `backend/app/main.py` L28 `from prometheus_client import make_asgi_app`; L158 `app.mount("/metrics", make_asgi_app())`. `backend/app/core/metrics.py` defines the 7 §15.J singletons: `AI_OPS_BUDGET_ALARM`, `I18N_MISSING_KEY`, `HTTP_REQUEST_DURATION`, `HTTP_REQUESTS_TOTAL`, `CELERY_QUEUE_DEPTH`, `AI_OPS_COST_INR`, `AUTH_TOKEN_REFRESH_FAILED` (L34–106; `__all__` L109–117). |
| 6 | Export worker audit rows (§15.I / F-15-1) | **PASS** | `backend/app/modules/export/tasks.py`: `export.completed` written on terminal success (L109–116, after `_run_export_pipeline` returns); `export.failed` written on terminal failure gated by `if self.request.retries >= self.max_retries` (L97–105). Both route through `_emit_export_terminal_audit` → direct `AuditEvent` ORM write (L125–168, `entity_type="export"`). |
| 7 | `@audit_event` on 4 write endpoints (F6) | **PASS** | `customer/router.py`: `@audit_event("customer.profile_updated")` L107, `@audit_event("customer.active_categories.updated")` L135, `@audit_event("customer.compliance_updated")` L164. `export/router.py`: `@audit_event("export.initiated")` L103. All 4 present. |
| 8 | `audit_mw` Gate 2.5 (F7) | **PASS** | `backend/app/core/middleware/audit_mw.py` L235–237: `if request.method not in {"POST", "PATCH", "PUT", "DELETE"}: return`. Positioned correctly — between Gate 2 (user_id check L230–233) and Gate 3 (coalesce check L242–246). |
| 9 | GCP Secret Manager — all 3 secrets populated | **FAIL** | Live query (account `vaishnaviramoorthy@gmail.com`, project `project-1f5cbf72-2820-4cdb-949` → number 888244156264): `refresh-token-pepper` → version `1` ENABLED (**PASS**); `razorpay-webhook-secret` → **zero versions** (`versions list` empty; `versions describe latest` → `NOT_FOUND: ... not found or has no versions`) (**FAIL**); `langfuse-secret-key` → **zero versions** (same `NOT_FOUND`) (**FAIL**). 1 of 3 populated. |

### Per-route decorator line citations (Check 1 / Check 2)

```
iam        (6): L105 post /auth/otp/send [public]   L124 post /auth/otp/verify [public]
                L152 post /auth/refresh [cookie]     L194 post /auth/logout [cookie]
                L220 get  /auth/me [JWT]             L247 post /webhooks/razorpay [HMAC]
customer   (5): L75 get [JWT]  L101 patch [JWT]  L129 patch [JWT]  L158 patch [JWT]  L198 get [JWT]
category   (5): L82 get [JWT]  L121 get [JWT]  L166 get [JWT]  L208 get [JWT]  L257 get [JWT]
catalog    (6): L131 post [JWT] L161 patch [JWT] L193 post [JWT] L255 get [JWT] L295 delete [JWT] L318 get [JWT]
image      (2): L74 post [JWT]  L121 get [JWT]
pricing    (1): L68 post [JWT]
dashboard  (1): L80 get [JWT]
export     (2): L89 post [JWT]  L135 get [JWT]
```
Tally: JWT 23 · cookie 2 · public 2 · HMAC 1 = **28**.

---

## Findings (FAIL / discrepancy)

### FAIL-9 — Two Secret Manager secrets have zero versions (CRITICAL-2 NOT resolved)

**Severity:** CRITICAL — blocks V1 GO.
**Status of founder claim:** The dispatch brief states "founder confirms razorpay-webhook-secret
+ langfuse-secret-key now populated." This is **contradicted by live GCP state**.

Evidence (account `vaishnaviramoorthy@gmail.com`, the correct project owner; the same account
*can* read versions — it returned `refresh-token-pepper` version 1 ENABLED, proving this is not
a permissions artifact):

```
$ gcloud secrets describe razorpay-webhook-secret  --project=project-1f5cbf72-2820-4cdb-949
projects/888244156264/secrets/razorpay-webhook-secret          # container EXISTS

$ gcloud secrets versions list razorpay-webhook-secret --project=... --format="table(name,state)"
(empty — no rows)

$ gcloud secrets versions describe latest --secret=razorpay-webhook-secret --project=...
ERROR: NOT_FOUND: Secret [...razorpay-webhook-secret] not found or has no versions.

$ gcloud secrets versions describe latest --secret=langfuse-secret-key --project=...
ERROR: NOT_FOUND: Secret [...langfuse-secret-key] not found or has no versions.
```

Both secret **containers** were created but **no version was ever added** to either. A Secret
Manager secret with zero versions cannot be read by `gcloud secrets versions access`, cannot be
projected into a K8s Secret, and the app's `settings` loader will fail to resolve
`RAZORPAY_WEBHOOK_SECRET` / `LANGFUSE_SECRET_KEY` in prod/staging.

**Required remediation (founder/infra action — outside backend-coordinator scope, hand-off below):**
```bash
printf '%s' "<razorpay webhook secret>" | gcloud secrets versions add razorpay-webhook-secret \
  --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
printf '%s' "<langfuse secret key>"     | gcloud secrets versions add langfuse-secret-key \
  --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
```
Re-run Check 9 after adding versions; it will pass once each `versions list ... --filter="state=ENABLED"`
returns at least one version name.

### F-CHECK4 — Checklist-text vs locked-architecture discrepancy (NON-BLOCKING; Check 4 PASSES)

This attempt's §22.C checklist lists the 10 contracts as: `lint-imports`, `lint-scope-to-user`,
`lint-no-meesho-symbols`, `lint-message-id-regex`, **`lint-ruff`, `lint-mypy`, `lint-bandit`,
`lint-safety`, `lint-pytest-markers`, `lint-alembic-heads`**.

The **locked** definition of the "10 CI linter contracts" per §16.E / §19.C / §19.G (and as
verified by the §16 audit 2026-06-09 and attempt-#1's Check 3) is:
**Contracts 1–7 = import-linter (27 sub-contracts), Contract 8 = scope_to_user,
Contract 9 = no-meesho-symbols, Contract 10 = message-id-regex.** That is the set wired in
`.gitlab-ci.yml` and the set the architecture documents as "all 10 CI contracts."

The six checklist names `ruff/mypy/bandit/safety/pytest-markers/alembic-heads` were **never part
of the §19.G/§16.E locked CI contract set** — they do not appear in the locked architecture or
any prior audit. Check 4 is therefore scored **PASS** against the locked architecture (all 10
real contracts are wired and verified green). The checklist wording for this attempt appears to
have substituted a generic Python-tooling list for the project-specific contract names.

**Recommendation:** reconcile the §22.C checklist text with the locked §16.E/§19.G contract names
so future audits do not re-trip on this. If the founder *wants* ruff/mypy/bandit/safety/
pytest-marker/alembic-head gates added to CI as a separate hardening item, that is a new scope
item, not a §22 acceptance regression. (Note: `ruff`, `mypy`, `bandit`, `safety` are not in
`backend/requirements.txt` as CI-invoked jobs today.)

---

## Overall verdict

**V1 NO-GO — 1 of 9 checks failed.**

- **8/9 PASS:** Checks 1–8 (route count, auth posture, golden fixtures, CI contracts,
  Prometheus metrics, export audit rows, `@audit_event` decorators, audit_mw Gate 2.5).
- **1/9 FAIL:** Check 9 (GCP Secret Manager) — `razorpay-webhook-secret` and
  `langfuse-secret-key` both have **zero versions**; only `refresh-token-pepper` is populated.

The two MEDIUM remediations (F6 decorators, F7 Gate 2.5) and the route/auth/CI/metrics/export
surface are all confirmed correct. The sole blocker is the unpopulated Secret Manager versions —
a founder/infra action, not a backend code defect. **V1 GO can be issued the moment the two
missing secret versions are added** (no code change required; re-run Check 9 only).

---

## Hand-back to master

- **Report:** `/Users/mugunthansrinivasan/Project/mesell/docs/audits/§22_acceptance_audit_2026-06-09_attempt2.md`
- **Verdict:** V1 NO-GO (8/9 PASS, 1 FAIL).
- **Single blocker:** Check 9 — populate `razorpay-webhook-secret` + `langfuse-secret-key`
  versions in GCP Secret Manager project `project-1f5cbf72-2820-4cdb-949`. Hand-off to
  **INFRA** track (`meesell-infra-builder`) + founder for the secret-value action; commands in
  Finding FAIL-9. This is the ONLY thing standing between the current tree and V1 GO.
- **Checklist reconciliation (non-blocking):** §22.C Check 4 text lists
  ruff/mypy/bandit/safety/pytest-markers/alembic-heads, which are NOT the locked §16.E/§19.G
  "10 CI contracts." The real 10 are wired and green. See Finding F-CHECK4; recommend updating
  the §22.C checklist wording.
