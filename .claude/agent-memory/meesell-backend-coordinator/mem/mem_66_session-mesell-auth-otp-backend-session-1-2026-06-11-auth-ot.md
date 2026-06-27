## Session mesell-auth-otp-backend-session-1 — 2026-06-11 — auth-otp BACKEND group merged (PR #44, night run)
Re-audit verdict: backend 100% built/contract-correct (FEATURE_PLAN's 2026-06-10 audit said ~95%). The "missing/verify" items were dispatch-template path mismatches vs as-built, NOT gaps. Reconciliation worth remembering for every future feature re-audit:
- **config lives at `backend/app/shared/config.py`** (the §5.D-locked path) — NOT `backend/app/config.py`. Plan templates that say `app/config.py` are wrong; trust §5.D.
- **Lua rotation is inlined as `REFRESH_ROTATE_LUA` in `core/auth.py`** — NOT a standalone `iam/lua/rotate_refresh.lua`. Body is verbatim §7.B.3; EVALSHA+EVAL fallback via `shared.valkey.eval_lua_script`; SCRIPT LOAD once cached on `_refresh_rotate_sha`.
- **`users` table ships in baseline migration `935e55b4852c`** (the 13-table baseline) — there is NO separate `iam_users` migration. Any plan asking to "create iam_users migration" is already satisfied.
- **iam tests live at `tests/modules/iam/` (4) + `tests/integration/test_iam_*` (3) + `tests/test_core_auth*` (3)** — NOT `tests/unit/iam/`. testpaths=tests, asyncio_mode=auto, 6 strict markers.
All 5 FE-D5 critical checks verified directly in core/auth.py: HMAC-with-pepper key `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}`, secrets.compare_digest, cookie Path=/api/v1/auth, ACCESS_TOKEN_TTL_SECONDS (JWT_EXPIRY_DAYS gone), no-`*` CORS validator.

Process:
- Branch was cut from origin/develop which ALREADY carries the iam code → ZERO construction diff. An empty PR can't be opened, so the backend group's tracked contribution was a verification record (`docs/plans/features/auth-otp/BACKEND_VERIFICATION.md`) — a legitimate lead-owned artifact, not invented specialist work.
- Integration branch named `feature/auth-otp/integration` per the night-run amendment (NOT the bare `feature/auth-otp` the plan §Branch setup uses). F3 protection via GH API needs a **raw JSON --input body** (the -f/-F flags mangle null/int types → 422). required_approving_review_count=0, allow_force_pushes/deletions=false.
- **GitHub blocks self-approval when the same gh account creates AND reviews a PR** ("Can not approve your own pull request"). The squash-merge still succeeds (`gh pr merge --squash --delete-branch`); record the lead gate decision as a PR **comment** instead. This will recur on every single-account night run — don't treat it as a failure.
- Test env note: local night runs have NO dev tunnel (Postgres 5433 / Valkey 6381 down). iam suite → 19 passed / 3 skipped / 6 errors; skips+errors are infra-gated + pre-existing (matches G-pass note). Green baseline for no-tunnel = the 19 pure-function/contract tests + 27 clean collection.

Files: BACKEND_VERIFICATION.md (on branch, merged via #44 SHA af6a619); feature_board_backend.md (IN REVIEW→MERGED, moved to Recently merged); STATUS_BACKEND.md (UPDATE block); auth_otp_feature.md (COMPLETE outcome); this entry. NO STATUS_MASTER.md write (master owns it). Master tree branch never switched (worked entirely in /tmp/mesell-wt/auth-otp-be, now removed).

Next: infra group lands feature/auth-otp/infra → integration next; THEN founder-gated integration→develop PR; THEN backend lead stamps V1_FEATURE_SPEC §F1 + BACKEND_ARCHITECTURE §7 (deliverables #4/#5).
