---
name: discipline-no-premature-dispatch
description: Founder ruling 2026-06-05 (FE-D7) — NO specialist dispatch until full FRONTEND_ARCHITECTURE.md is locked end-to-end. Even if individual gating sections (§3, §6) lock early, dispatch waits.
metadata:
  type: project
---

# FE-D7 — Documentation-first discipline (founder ruling 2026-06-05)

## The ruling, verbatim

> "We are doing the architecture documentation right. Until full finish, don't execute the implementation."

## What it means in practice

Even when §3 (File Structure) + §6 (Third-Party Tool Selection) are LOCKED — which would technically unblock the first specialist dispatch (clean-slate Angular scaffold via `meesell-angular-service-builder`) — I do NOT dispatch. The discipline says the **entire** FRONTEND_ARCHITECTURE.md must be locked end-to-end before any code lands.

## Why this is correct

Three reasons it's worth the patience:

1. **Build-half-then-retrofit prevention.** If we scaffold `frontend/` against §3 + §6 today, then §18 (the 11-primitive contract) lands in a future review with a different interface shape, the specialist either retrofits or carries dead code. Cost of retrofit at scaffold-time = small. Cost of retrofit after specialists have populated component bodies = large.

2. **Cross-section consistency check.** Reviewing all sections sequentially means dependencies show up cleanly. e.g., §17 (communication rules) might constrain how §4 services expose their API. If §4 locks before §17, we get a mismatched contract.

3. **Founder mental model alignment.** The founder is internalising the full architecture turn-by-turn. Skipping ahead to code means the founder is approving implementations against a partial picture. Documentation-first means the founder ratifies the WHOLE picture before any line of code is written.

## How to apply

**For me (coordinator) — every time a specialist or master session asks "can we dispatch yet?":**
- Answer: NO, until §22 + §22A LOCKED. Those are the last 2 sections by my recommended order. When they LOCK, the readiness check completes and dispatch is authorised.
- Cite FE-D7 + this memory file as the authority.

**For all 3 frontend specialists when surfaced:**
- They CAN read FRONTEND_ARCHITECTURE.md to understand the contract they'll execute against
- They CANNOT write any production code under `frontend/src/` until the documentation is fully locked
- The existing React scaffold under `frontend/src/` remains untouched (per FE-D1) until the architecture-complete dispatch arrives

**For STATUS_FRONTEND.md updates:**
- Every "Next" line in the Updates Log must reference the next section to review, NEVER "dispatch specialist X"
- Until §22 + §22A LOCKED, every "Blockers" line must not list a code-side blocker — only documentation review cadence

## Roadmap to dispatch-ready

After §6 LOCKED, the remaining LOCK queue (recommended order):

| # | Section | Status | Notes |
|---|---|---|---|
| 1 | §2 Feature Catalog | SKELETON | Quick — already implicit via §3 + §23 |
| 2 | §4 core/ Cross-Cutting Foundation | SKELETON | Has substantial JWT content from §1 reconciliation; mostly editorial DRAFT promotion |
| 3 | §5 shared/ deep contract | SKELETON | Stateless primitives list expansion |
| 4 | §5A Design System Tokens | SKELETON | Color / typography / spacing / elevation / motion / breakpoints |
| 5 | §17 Service-Component Communication Rules | SKELETON | 6 rules briefly drafted — high leverage, short |
| 6 | §18 11 Primitives + Form Renderer | SKELETON | The wizard renderer contract — most important after auth |
| 7 | §7 auth feature deep spec | SKELETON | Honours FE-D5 + FE-D6 + ng-otp-input integration |
| 8 | §8 onboarding feature deep spec | SKELETON | 3-phase wizard, separate from catalog wizard |
| 9 | §9 dashboard feature deep spec | SKELETON | MatTable + pagination + filters |
| 10 | §10 smart-picker feature deep spec | SKELETON | Description input + 3 cards + browse fallback |
| 11 | §11 catalog-form feature deep spec | SKELETON | THE biggest feature — wizard renderer + autofill overlay + autosave + draft recovery |
| 12 | §12 images feature deep spec | SKELETON | 4-slot drag-drop + ngx-image-compress + precheck poll |
| 13 | §13 preview feature deep spec | SKELETON | 3 preview surfaces (feed/detail/mobile) |
| 14 | §14 pricing feature deep spec | SKELETON | MRP + slider + breakdown + chart.js |
| 15 | §15 export feature deep spec | SKELETON | Validation + poll + signed-URL download |
| 16 | §5B Wireframe & Mockup Methodology | SKELETON | Process artefact — 3 stages |
| 17 | §16 Cross-Cutting Walkthroughs | SKELETON | State decision tree + i18n + caching + offline + plan gating |
| 18 | §19 Test Strategy + Performance Budget | SKELETON | Tables already drafted |
| 19 | §20 Build & Deployment Topology | SKELETON | Dockerfile + nginx + ngsw-config |
| 20 | §21 SOLID, DRY, Modern Techniques | SKELETON | Substantial content drafted |
| 21 | §22 Acceptance & Sign-Off | SKELETON | Checklist mirroring V1 §8 |
| 22 | §22A Risk Register | SKELETON | 11 risks enumerated |

**§22 + §22A LOCKED = dispatch authorisation activates.** That triggers the first specialist dispatch (`meesell-angular-service-builder` for the clean-slate scaffold).

## Edge cases this discipline protects against

- "Can we just scaffold the empty folders so the React deletion happens?" → NO. React stays until §22 LOCKED.
- "Can we let the service-builder start on AuthService since §4 is mostly done?" → NO. §4 isn't formally LOCKED yet.
- "Can we install dependencies into package.json early so npm install isn't on the critical path?" → NO. The npm install is part of the first dispatch's scaffold.
- "Can we publish the design tokens to a CDN to validate them visually?" → NO. Design tokens get rendered when §5A is locked AND the styler specialist is dispatched.

If any of these edge cases need exception, founder approval per turn — not a blanket pre-authorization.
