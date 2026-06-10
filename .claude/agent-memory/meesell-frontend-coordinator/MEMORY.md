# Memory — meesell-frontend-coordinator

## Agent Identity
Frontend coordinator for MeeSell. Orchestrates the 3 frontend specialists (component, service, ui-styler). Owns STATUS_FRONTEND.md, app.config.ts, app.routes.ts, FRONTEND_ARCHITECTURE.md, integration smoke tests. Decentralized memory ecosystem.

## MEMORY.md

### auth-otp (Feature 1 — active)
- [auth_otp_feature.md](auth_otp_feature.md) — auth-otp: your role as frontend lead, 3-specialist dispatch order (service-builder → component-builder → ui-styler), branch ownership, FE-D5 contracts to enforce in PR review

### Prior sessions
- [Framework gate](framework_gate.md) — Angular 18 ratified 2026-06-05; React scaffold to be deleted
- [Architecture doc authored](architecture_doc_authored.md) — FRONTEND_ARCHITECTURE.md SKELETON+§0 LOCKED+§1 DRAFT
- [Third-party tool picks](third_party_picks.md) — locked dependency set for V1
- [Locked decisions inherited](locked_decisions_inherited.md) — CLAUDE.md D9-D14 + MVP §4 + Philosophy M1/M9
- [Cross-track contracts](cross_track_contracts.md) — what backend/data/ai must hand us
- [Backend handoff: JWT session pattern](backend_handoff_jwt_session_pattern.md) — FE-D5+FE-D6 deltas the founder takes to backend session 2026-06-05
- [Section 1 locked](section_1_locked.md) — §1 LOCKED 2026-06-05 post backend ratification + 3 founder-ratified strengthenings (Lua EVAL, HMAC-pepper, Path=/api/v1/auth) + pre-deploy checklist
- [Section 3 locked](section_3_locked.md) — §3 LOCKED 2026-06-05 with design-system reframed as style architecture surface; 5 locked decisions; dispatch order for 3 specialists
- [Discipline: no premature dispatch](discipline_no_premature_dispatch.md) — FE-D7 founder ruling 2026-06-05; full architecture must be LOCKED end-to-end before any specialist dispatch; roadmap of 22 remaining sections in recommended LOCK order
- [Section 2 locked](section_2_locked.md) — §2 LOCKED 2026-06-05 with auth+onboarding merger into single account feature (9 folders, 4 routes, 7 endpoints, 2 backend peers iam+customer); AMENDMENT 2026-06-05B propagated to §3 + §6 + §7 + §8 (reserved) + §23 + TOC
- [Section 4 locked](section_4_locked.md) — §4 LOCKED 2026-06-05; AuthService API + 4 interceptors + ApiClient with retryOn503 opt-in + ErrorService + NetworkService + 9 cross-feature models. Looks 2/3 deferred to V1.5. FE-D8: coordinator owns drill-down depth call for upcoming sections.
- [FULL DOC LOCKED](full_doc_locked.md) — FRONTEND_ARCHITECTURE.md fully LOCKED end-to-end 2026-06-05; 22 of 23 sections LOCKED (§8 RESERVED merged into §7); FE-D7 satisfied; specialist dispatch authorisation ACTIVATED; pre-deploy gates remain on REFRESH_TOKEN_PEPPER + backend iam + CORS
- [Angular 18 → 20 upgrade](angular_20_upgrade_2026_06_08.md) — founder-approved 2026-06-08; supersedes locked D9 "Angular 18"; Material v20 variant-prefixed tokens fixed in _component-overrides.scss (button/card/form-field/menu); dev build 5.4s, ng serve returns HTTP 200; transloco 7→8; @angular-eslint + vitest-angular still on v18 toolchain (non-blocking)
- [Wave 2B scaffold](wave_2b_scaffold_2026_06_08.md) — 2026-06-08 clean re-scaffold: OLD Material stack archived to archive/frontend_angular_material/; NEW = Angular 21.2.16 + PrimeNG 21.1.9 + @primeuix/themes 2.0.3 + Tailwind 4.3.0. Tailwind wired via PostCSS (postcss.config.mjs + styles.css `@import "tailwindcss"`); @angular/build:application builder; vitest 4 default; zoneless+strict defaults. Build green 2.278s. Coordinator executed via Bash (no specialist dispatch); ui-styler takes 2B-2. PrimeNG theme via providePrimeNG() not CSS import.
