---
name: project-fe-d5-token-model
description: FE-D5 split-token + server-side revocation auth pattern — legal narrative for Privacy "How we protect" and DPA TOMs
metadata:
  type: project
---

# FE-D5 Token Model — Legal Implications

**Date ratified:** 2026-06-05 (CLAUDE.md amendment + FEA §1.F + BEA §4.B).

## What changed
- Access JWT: in-memory in the Angular `AuthService.accessToken` signal; **never** localStorage / sessionStorage / IndexedDB; 15-min TTL (env-driven, prod 900 s).
- Refresh token: opaque `secrets.token_urlsafe(48)`; HttpOnly + Secure + SameSite=Strict cookie scoped to `Path=/api/v1/auth; Domain=.mesell.xyz`; 7-day TTL.
- Refresh allowlist: Valkey DB 0 key `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` (HMAC with backend-only pepper, not plain SHA-256 — defends against Valkey-only breach).
- Rotation: Lua `EVAL` atomic check-then-DEL-then-SET (NOT MULTI/EXEC — no race window). `secrets.compare_digest()` for constant-time lookup.
- Server-side revocation: logout DELs the allowlist entry; refresh fails immediately on next call.

## Why
- Tokens never in browser storage = no XSS exfiltration of the long-lived credential.
- HttpOnly cookie = JS cannot read it.
- SameSite=Strict = no CSRF on the refresh endpoint.
- HMAC pepper = Valkey breach alone is not enough to forge refresh tokens.
- 15-min access TTL = at most 15-min compromise window from access-token exfiltration.
- Server-side revocation = instant force-logout possible.

## How to apply (drafting language)
**Privacy Policy §"How we protect your data":**
> "Your session is protected by short-lived access tokens (≤15 minutes) held only in browser memory, paired with a separate refresh credential delivered as a strict, secure, browser-only cookie. We maintain server-side records that let us revoke any session immediately on logout or on detection of unusual activity. Your tokens are never stored in browser local storage and are never transmitted in URLs."

**DPA Annex 2 — Technical and Organisational Measures (TOMs):**
- Authentication: stateless JWT + opaque refresh token; HMAC-SHA256 with private pepper for allowlist key derivation; constant-time comparison; atomic Lua-script rotation; server-side revocation.
- Token TTL: access ≤15 min, refresh ≤7 days, both env-driven for staging tests.
- Storage: access token in-memory only; refresh token in HttpOnly+Secure+SameSite=Strict cookie scoped to /api/v1/auth.

**IT Act §43A "reasonable security practices":** the FE-D5 model is materially stronger than the previous "JWT in localStorage" baseline and is defensible as a "reasonable security practice" under §43A jurisprudence. Reference for breach-impact paragraphs in incident response.

## Links
- `docs/FRONTEND_ARCHITECTURE.md` §1.F (token storage)
- `docs/BACKEND_ARCHITECTURE.md` §4.B (auth contract)
- `docs/INFRASTRUCTURE_ARCHITECTURE.md` §4 (jwt-secret + refresh-token-pepper secret)
- See [[session-2-legal-architecture]] §1.B for the topology diagram annotation.
