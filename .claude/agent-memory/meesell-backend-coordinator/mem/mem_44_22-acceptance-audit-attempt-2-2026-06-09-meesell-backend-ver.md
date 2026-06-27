## §22 Acceptance Audit Attempt #2 — 2026-06-09 (meesell-backend-verification-22-acceptance-2)

Re-audit of all 9 §22.C acceptance checks after attempt-#1 remediation. **Verdict: V1 NO-GO (8/9 PASS, 1 FAIL).**

### Results
- Checks 1-8 PASS. Check 9 (GCP Secret Manager) FAIL.
- C1 route count = exactly 28 (iam 6 / customer 5 / category 5 / catalog 6 / image 2 / pricing 1 / dashboard 1 / export 2).
- C2 auth posture 23 JWT / 2 cookie / 2 public / 1 HMAC — EXACT. iam contributes 1 JWT (/auth/me) + 2 cookie (refresh/logout, `refresh_token: Annotated[Optional[str], Cookie()]`) + 2 public (otp/send, otp/verify) + 1 HMAC (razorpay webhook). Remaining 22 routes all `Depends(get_current_user)`.
- C3 15 golden fixtures fixture_01..fixture_15 in backend/tests/integration/golden_round_trip/.
- C5 prometheus make_asgi_app mounted /metrics (main.py L28+L158); 7 §15.J singletons in core/metrics.py.
- C6 export/tasks.py: export.completed (terminal success L109-116) + export.failed (gated `retries >= max_retries` L97-105) both via `_emit_export_terminal_audit`.
- C7 4 @audit_event: customer.profile_updated L107, customer.active_categories.updated L135, customer.compliance_updated L164, export.initiated L103.
- C8 audit_mw Gate 2.5 L235-237 `if request.method not in {"POST","PATCH","PUT","DELETE"}: return` — correctly between Gate 2 (user_id) and Gate 3 (coalesce).

### KEY FINDING — CRITICAL-2 NOT actually resolved (founder claim contradicted)
Founder told this audit razorpay-webhook-secret + langfuse-secret-key are "now populated." LIVE GCP says otherwise. All 3 secret CONTAINERS exist in project-1f5cbf72-2820-4cdb-949 (num 888244156264), but:
- refresh-token-pepper → version 1 ENABLED (PASS)
- razorpay-webhook-secret → ZERO versions
- langfuse-secret-key → ZERO versions
`gcloud secrets versions describe latest --secret=X` → `NOT_FOUND: ... not found or has no versions` for both. Account vaishnaviramoorthy@gmail.com (correct owner) CAN read versions (saw pepper v1), so it's NOT a perms artifact — the versions genuinely don't exist. **A secret container with zero versions reads as "exists" via `secrets describe` but is unusable.** Lesson: ALWAYS verify with `versions list --filter="state=ENABLED"` OR `versions describe latest`, NEVER trust `secrets describe` (container) alone, and NEVER take a "populated" claim at face value for an acceptance gate.

### TOOLING gotcha
gcloud is NOT on the sandbox PATH and `which gcloud` fails in sandbox. Binary lives at /opt/homebrew/bin/gcloud. Must invoke by absolute path WITH `dangerouslyDisableSandbox: true` for read-only `gcloud secrets versions list/describe`. The `--filter="state=ENABLED"` on an empty secret emits `WARNING: filter keys ... not present in any resource` (because the resource list is empty) — that warning IS the signal of zero versions; confirm with `versions describe latest`.

### CHECK 4 checklist-vs-locked discrepancy (non-blocking, scored PASS)
This attempt's §22.C Check-4 text listed 10 contracts as lint-imports + lint-scope-to-user + lint-no-meesho-symbols + lint-message-id-regex + ruff + mypy + bandit + safety + pytest-markers + alembic-heads. That is WRONG vs locked architecture. The LOCKED "10 CI contracts" (§16.E/§19.C/§19.G, verified by §16 audit 2026-06-09 + attempt-1 Check 3) are: Contracts 1-7 import-linter (27 sub-contracts in tests/lint/import_rules.toml) + C8 check_scope_to_user.py + C9 check_no_meesho_symbols_outside_export.py + C10 check_message_id_regex.py. .gitlab-ci.yml lint: stage (L120-140) wires exactly these 4 commands. ruff/mypy/bandit/safety are NOT in the locked set and NOT CI-invoked today. Scored Check 4 PASS against locked architecture; flagged for §22.C checklist-text reconciliation. Lesson: when a checklist's enumerated names diverge from a LOCKED spec, audit against the locked spec and surface the divergence — don't fail a real PASS on a stale checklist.

### Single blocker to V1 GO
Populate 2 SM versions (founder/INFRA action, zero code change): `gcloud secrets versions add razorpay-webhook-secret/langfuse-secret-key --data-file=-`. Re-run Check 9 only. Everything else green.

Files touched: docs/audits/§22_acceptance_audit_2026-06-09_attempt2.md (new), docs/status/STATUS_BACKEND.md (STATUS block), this MEMORY.md. No code modified, no sub-agent dispatch (audit-only). BACKEND_ARCHITECTURE.md NOT touched per §5.0.

---
