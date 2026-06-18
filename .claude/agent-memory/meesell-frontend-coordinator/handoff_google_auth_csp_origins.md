# Handoff → infra: Google Sign-In CSP + OAuth client/origins

**From:** meesell-frontend-coordinator (Frontend Lead)
**To:** meesell-infra-builder
**Date:** 2026-06-18
**Feature:** google-auth
**Design:** docs/plans/google_auth/GOOGLE_AUTH_DESIGN_FRONTEND.md §E.2/§E.3

## 1. Provision two Google OAuth Web clients (OQ-8)
- DEV client: Authorized JS origin = the **shell** dev origin `http://localhost:4200`
  (users hit the shell, NEVER the mfe-auth remote at :4206).
- PROD client: Authorized JS origin = the production app (shell) origin.
- The SAME client id must be pinned on the backend for ID-token `aud` verification.
- FE currently ships placeholders `DEV_GOOGLE_WEB_CLIENT_ID...` / `PROD_GOOGLE_WEB_CLIENT_ID...`
  in `frontend/libs/env/environment.ts` + `environment.prod.ts`. Replace with real ids
  (in lockstep with backend) — these are PUBLIC, not secrets.

## 2. CSP add-only (C-CSP-1, Sub-plan 7) — when CSP lands
GIS needs (ADD-ONLY; must NOT strip existing CORS / refresh-cookie behaviour):
- `script-src https://accounts.google.com/gsi/client`
- `frame-src https://accounts.google.com/gsi/`
- `connect-src https://accounts.google.com/gsi/`
- `style-src https://accounts.google.com/gsi/style` (if styled)

GIS is loaded as a runtime browser asset (lazy `<script>` inject), NOT an npm dep — zero
federation share-graph impact. No CSP exists today; this is a Sub-plan 7 deliverable.

## Action
Provision the 2 OAuth clients + return the ids. Track the CSP additions for SP7. 48h SLA on
the OAuth-client provisioning (blocks live Google testing, not the FE merge).

