---
name: architecture-doc-authored
description: docs/FRONTEND_ARCHITECTURE.md was authored 2026-06-05 — mirrors BACKEND_ARCHITECTURE.md structure with SKELETON+§0 LOCKED+§1 DRAFT, founder reviews remaining sections one-by-one
metadata:
  type: project
---

# FRONTEND_ARCHITECTURE.md authored 2026-06-05

## Why this matters

The frontend track had no architecture doc until this session. STATUS_FRONTEND.md was the only frontend reference. That's not enough to dispatch specialists — specialists need a locked contract.

I authored `docs/FRONTEND_ARCHITECTURE.md` following the exact pattern set by BACKEND_ARCHITECTURE.md:
- Section 0 (Premises) fully authored, marked LOCKED
- Section 1 (System Topology) authored, marked DRAFT (founder reviews next)
- Sections 2-23 in SKELETON form (paragraph each, ready for per-section locking)

## How to apply

**For dispatching specialists:**
- A specialist may NOT begin code on a feature whose architecture section is still SKELETON
- The first dispatch under this contract is the clean-slate scaffold — depends on §3 (File Structure) + §5A (Design System) + §6 (Third-Party Tools) being LOCKED
- §11 (catalog-form) is the biggest single feature — defer its lock until §18 (primitives contract) is locked first; the two are tightly coupled

**For founder review cadence:**
- Recommend §1 next (topology gates §20 build/deploy)
- Then §3 + §6 together (enables first specialist dispatch — clean scaffold)
- Then §5A (design tokens before any component renders)
- Then §17 (communication rules — affects every later feature spec)
- Then features in dependency order: §7 (auth) → §8 (onboarding) → §9 (dashboard) → §10 (smart picker) → §18 (primitives contract) → §11 (catalog form) → §12 (images) → §13 (preview) → §14 (pricing) → §15 (export)
- Final: §19 (test strategy + perf budget), §22 (acceptance), §22A (risk register)

**For preserving the lock discipline:**
- I (the coordinator) do NOT flip sections from DRAFT to LOCKED — only the founder does
- Specialists that try to start work on a SKELETON section get redirected to "wait for founder lock"
- If a specialist needs information from a still-SKELETON section, surface a blocker in STATUS_FRONTEND.md and wait

## What the doc contains (capability index)

- 11 input primitives + dispatcher (the form-renderer spine) — §0.D, §18
- 12 routes (10 V1 + /onboarding + /profile) — §23
- Features-first folder structure under `features/` — §3
- 3 HTTP interceptors (JWT, Locale, Error) in canonical order — §4
- Design system flowing M3 tokens through both Material and Tailwind — §5A
- Wireframe/mockup methodology (Excalidraw → Figma → Storybook prototype) — §5B
- Third-party deps locked at 14 packages — §6
- 6 inter-feature communication rules — §17
- SOLID/DRY/modern-techniques charter — §21
- Performance budget for Tirupur 2G/3G mobile — §19
- 10-item risk register — §22A
