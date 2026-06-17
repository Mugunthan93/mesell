# Handoff → meesell-infra-builder — MF mfe-auth deploy (D-auth hosting + R-SP6-6/C-CSP-1)

**From:** meesell-frontend-coordinator (Frontend Lead)
**Date opened:** 2026-06-11
**Feature:** mfe-auth (MF Sub-Plan 06) — the **6th and FINAL** remote extraction
**SLA:** 48h before escalation to founder via STATUS_MASTER.md
**Board row:** feature_board_frontend.md → Inter-lead requests open (outgoing).
**Group PR:** #95 squash `8e90363` (frontend→integration, lead-gated MERGED).
**Founder gate:** #96 integration→develop OPEN (founder's gate per D1 — not lead-approved).

## Context
SP06 mfe-auth is the LAST extraction. With #96 merged, ALL SIX Native Federation
remotes coexist on develop:
- mfe-pricing  → port 4201
- mfe-export   → port 4202
- mfe-onboarding → port 4203
- mfe-dashboard → port 4204
- mfe-catalog  → port 4205
- **mfe-auth    → port 4206  (THIS slice — login / signup / otp-verify)**

After this, the only remaining sub-plan is **SP07 (cutover)** — shell relocation
(D43), version-pinned per-env manifests (D44), CSP go-live (D42), and discharge of
all 6 Gate-4 C-conditions. This memo is the LAST per-remote hosting request; it
completes the 6-remote topology for SP07's consolidated hosting wave.

## The asks (D-auth hosting, extends the existing SP01–05 pattern — RECORD-ONLY)
Consistent with the 5 prior outstanding inter-lead rows (per founder ruling: D13
hosting deferred to a consolidated wave; these are RECORD-ONLY so SP07 has the full
manifest of remotes to host):
1. **GCS prefix** `gs://meesell-frontend/{env}/mfe-auth/{version}/` (sixth remote).
2. **CI matrix unit** `apps/mfe-auth/**` as its own build unit in the
   dorny/paths-filter matrix (C-CI-1). `shared/**` (libs/) still rebuilds ALL.
3. **Prod manifest URL template** `remotes.mesell.xyz/{env}/mfe-auth/{version}/remoteEntry.json`.
4. **Singleton CDN rule (carried forward):** the CDN MUST serve the SAME
   `@mesell/core`, `@mesell/ui-kit`, `@mesell/composites` module URLs to the shell
   AND mfe-auth — mfe-auth is a **@mesell/core consumer** (AuthService.setSession via
   otp-verify), so a per-remote stale duplicate of `@mesell/core` = singleton drift
   = the C4 WRITE path breaks at runtime. mfe-auth + mfe-onboarding are the two
   @mesell/core-consuming remotes; both must resolve the identical `_mesell_core.js`
   URL as the shell.

## ⛔ R-SP6-6 / C-CSP-1 ESCALATION TO SP07 (the load-bearing item)
**mfe-auth federates PUBLIC pre-auth routes** (`/login`, `/signup`, `/otp-verify`,
all with NO `canActivate`). Its `remoteEntry.json` is fetched by an UNAUTHENTICATED
browser with NO Authorization header — the remote must be world-readable on the CDN.

Together with **SP04's public landing route** (mfe-dashboard `./LandingComponent`),
these are the **TWO highest-stakes CSP surfaces** in the whole migration:
- They load remote ESM from `remotes.mesell.xyz` into the shell origin pre-auth.
- The production CSP `script-src` / `connect-src` allowlist MUST include the remotes
  origin, or the public auth/landing pages white-screen for unauthenticated users.

**Resolution path (founder-RULED, do NOT improvise):**
- **D42 (RULED APPROVED 2026-06-11):** CSP is **ADD-ONLY**, authored at SP07,
  **dev-smoke-tested first**, staging/prod gated on a GREEN CSP smoke. It must NOT
  strip CORS nor the refresh-token `Set-Cookie` (Gate-4 Answer 4). This discharges
  **C-CSP-1** and resolves D14.
- **Ownership split (joint infra↔fe SP07 deliverable):** **frontend owns the CSP
  allowlist content** (which origins/directives); **infra owns the nginx/Traefik
  mechanism** that emits the header.
- C-CSP-1 stays OPEN until SP07 ships the dev-validated CSP. This memo is the formal
  record that mfe-auth (public auth) is the inbound surface that makes C-CSP-1 P0.

## Not a blocker for THIS gate (#96)
Dev validation uses localhost-served `remoteEntry.json` (port 4206), so the frontend
gate never blocks on the GCS/CDN surface. Hosting + CSP are SP07. This is a 48h-SLA
inter-lead record, not a blocker for the founder's #96 merge.

## How to resolve (decentralized memory protocol)
Read this memo + add YOUR OWN incoming-side row to YOUR board
(feature_board_infra*.md). Do NOT edit feature_board_frontend.md (sole-writer). When
the consolidated SP07 hosting wave lands all 6 prefixes + the CSP mechanism, the
Frontend Lead marks the open rows CLOSED on its own board.
