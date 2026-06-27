## Session 3 turn 8 — 2026-06-05 — FE-D5 ratification: 7 amendments applied to BACKEND_ARCHITECTURE.md + 3 cross-track doc amendments

Urgent cross-track amendment received from frontend coordinator (memo `.claude/agent-memory/meesell-frontend-coordinator/backend_handoff_jwt_session_pattern.md`) ratifying FE-D5 (no client-side token storage) + FE-D6 (env-driven lifetimes). Backend ratification complete — 7 amendments applied as instructed; 3 substantive coordinator counter-proposals raised on the pushback surface.

**Endpoint count: 25 → 27.** §0.C amendment block appended; §17 SKELETON refined to "27 endpoints" with FE-D5 column added. The 2 new endpoints (`POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`) are owned by the `iam` module and are non-JWT-protected (refresh cookie is the credential).

**§4.B amendment block** captures the split-token contract: access JWT shape `{sub, exp, plan}` UNCHANGED; TTL env-driven via `ACCESS_TOKEN_TTL_SECONDS` (replaces deprecated `JWT_EXPIRY_DAYS`); refresh token opaque `secrets.token_urlsafe(48)`; allowlist Valkey DB 0 `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}`; `secrets.compare_digest()` for constant-time lookup; cookie `Path=/api/v1/auth` (coordinator correction vs memo's `/auth` — memo path would not match the actual endpoint paths and break the browser cookie attach); rotation via **Lua script via EVAL** (coordinator counter-proposal vs memo's MULTI/EXEC — Lua is truly atomic single-round-trip CAS, MULTI/EXEC requires WATCH and has a race window).

**§4.G amendment block** captures CORS for the refresh cookie: `Access-Control-Allow-Credentials: true` on `/api/v1/auth/*`, `Access-Control-Allow-Origin` explicit (NEVER `*`), cookie `Domain=.mesell.xyz`, frontend `withCredentials: true` for `/auth/*` only.

**Pushback verdicts on items 1-5:**
1. **Rotation atomicity** — counter-propose **Lua script via EVAL** over MULTI/EXEC. Single-round-trip atomic DEL-old + SET-new; no race window. Founder to rule; MULTI/EXEC + WATCH acceptable fallback.
2. **`sha256(token)` vs `hmac_sha256(token, PEPPER)`** — counter-propose **HMAC-SHA256 with `REFRESH_TOKEN_PEPPER`**. Without pepper a Valkey-only breach lets an attacker compute SHA-256 of captured cookies; with pepper, attacker also needs backend-only secret from Secret Manager.
3. **5-min staging / 2-min dev refresh TTL conflict with rate-limit windows** — N/A. OTP keyspace (`otp:{phone}`) and refresh keyspace (`cache:refresh:{hmac}`) are independent; 60/h/user refresh limit does not collide with 3/h/phone OTP limit.
4. **`Path=/auth` cookie vs `/me`** — coordinator **corrected** the cookie path from `/auth` to `/api/v1/auth` because the actual endpoint paths are under `/api/v1/auth/*`. With this correction: `/me` (also under `/api/v1/auth/`) DOES receive the cookie, but `/me` consumes the access JWT in `Authorization` header only — the cookie reaching `/me` is harmless (not read). The 7-day refresh cookie does NOT extend to `/api/v1/products`, `/api/v1/categories`, etc., preserving minimal exposure.
5. **Other conflicts** — none spotted beyond items 1-4 above.

**Section status post-amendment.** §0 and §4 retain LOCKED status with append-only AMENDMENT blocks (audit trail preserved — original LOCKED text + 2026-06-05 amendment block visible side-by-side). §7, §15, §17, §19 remain SKELETON but refined to absorb the new contract (in-place edits as instructed — those sections were never LOCKED).

**Cross-track doc amendments confirmed.** V1_FEATURE_SPEC.md §F1 step 4 + acceptance criteria — append-only AMENDMENT blocks added. MVP_ARCHITECTURE.md §11.7 — AMENDMENT paragraph appended (does NOT modify existing prose). CLAUDE.md Decision 14 — final clause appended (does NOT rewrite existing prose).

**Files touched this turn: 4.**
- `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` — 7 amendments (§0.C + §4.B + §4.G + §7 + §15 + §17 + §19 + §5 env-var note)
- `/Users/mugunthansrinivasan/Project/mesell/docs/V1_FEATURE_SPEC.md` — §F1 step 4 + acceptance amendments
- `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` — §11.7 amendment paragraph
- `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` — Decision 14 final clause
- (this MEMORY.md update — does not count toward construction file count)

NO sub-agent dispatch. NO Section 5 deep content authored (out of scope this turn). NO touch to DATABASE_ARCHITECTURE.md or INFRASTRUCTURE_ARCHITECTURE.md (Valkey keyspace addition flagged optional in memo, deferred to database-builder).

Standing by to resume §5 dispatch on founder go. Frontend may flip FRONTEND_ARCHITECTURE.md §1 to LOCKED on the strength of this ratification. The 3 contested items (Lua-vs-MULTI/EXEC, HMAC-pepper, Path correction) are coordinator-proposed strengthenings — founder rules; if any are rejected, the frontend memo's original phrasings are accepted as-is.
