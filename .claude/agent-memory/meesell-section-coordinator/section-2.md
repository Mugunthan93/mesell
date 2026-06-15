# Section-2 (smart-picker) — Topic Memory

**Coordinator session:** mesell-section-2-coordinator-session-1
**Date started:** 2026-06-15
**Integration branch:** feature/section-2/integration
**Integration worktree:** /private/tmp/mesell-wt/section-2-integration

---

## Session start

## Session mesell-section-2-coordinator-session-1 — 2026-06-15

Fresh session: no prior section-2 topic memory existed.

### Context loaded

- SECTION_PARALLEL_MODEL.md (APPROVED 2026-06-15)
- MASTER_PLAN.md §1/§2/§4/§7
- SECTION_SUB_SESSION_PROTOCOL.md
- SECTION_DISPATCH_PROTOCOL.md
- _WORKTREE_PROTOCOL.md
- smart-picker FEATURE_PLAN.md (LOCKED, 92KB)
- V1_FEATURE_SPEC.md Feature 2

---

## Existing state survey findings

- Backend: `backend/app/modules/category/` is substantially built. 5 endpoints working. Rate limit, caching, graceful fallback, pg_trgm browse all implemented.
- Frontend: `frontend/apps/mfe-catalog/src/app/smart-picker/` exists with smart-picker component and category.service.ts. Auto-fire 400ms debounce pattern in place.
- Gap 1: `/categories/browse` route missing in Angular (backend endpoint exists and works).
- Gap 2: i18n `validation_message_id` for rate-limit was 2-segment ("rate_limit.exceeded") — violates 3-segment regex rule.
- Gap 3: PrimeNG abstraction wall: one raw `<button>` in smart-picker.component.ts where `<mee-button>` should be used.
- Gap 4: Smart picker UX uses auto-fire; founder wants Claude/ChatGPT-style entry page with submit-on-Enter.

---

## Founder decisions (2026-06-15)

1. **Trigger model**: Submit on Enter / Send button — LOCKED. Replaces auto-fire 400ms debounce.
2. **Error surfacing**: inline for validation/empty-state, mee-toast for transient (429/5xx), 401 silent logout.
3. **Refine-and-resend**: user edits description and submits again — each submit is a fresh AI call.
4. **FE serialization order**: Plans 3→4→1→2(FE) must serialize on feature/section-2/frontend (all touch same files). Backend Plan 2-W1 runs in parallel.

---

## Wave plan (4 plans, check-in gate passed 2026-06-15)

Wave plan files: `docs/plans/features/smart-picker/waves/plan-{1-4}-*.md`

| Plan | Scope | Lane | Status |
|---|---|---|---|
| Plan 1 | Manual browse fallback page (/categories/browse) | FE-only | PENDING (after Plan 4) |
| Plan 2-W1 | i18n message contract verification + fix | BE-only | ✅ DONE (squash 2766ed7) |
| Plan 2-W2 | Error message surfacing (FE inline + toast) | FE-only | PENDING (last in FE lane) |
| Plan 3 | PrimeNG correctness (button swap) | FE-only | ✅ DONE (squash 11531a4) |
| Plan 4 | Entry page redesign (submit-on-Enter) | FE-only | IN PROGRESS |

---

## Branch and commit state

| Branch | Last commit | Notes |
|---|---|---|
| feature/section-2/integration | 2766ed7 | Plan 3-B + Plan 2-W1 squashed in |
| feature/section-2/frontend | 646a370 | Plan 3-B commit pushed |
| feature/section-2/backend | 960ed70 | Plan 2-W1 commit pushed |

---

## Locked copy contract (from Plan 2-W1 audit)

See `docs/plans/features/smart-picker/waves/plan-2-error-messages.md` for the full 7-row contract.

Key rule: `smart_picker.ai.unavailable` and `smart_picker.budget.exceeded` are NOT error IDs — they're `fallback_offered: true` in the 200 body.

---

## Key technical findings

- `MeeButtonComponent` barrel path: `frontend/libs/ui-kit/index.ts` (NOT `src/index.ts`)
- `MeeButtonComponent` file: `frontend/libs/ui-kit/button/button.component.ts`
- `category-card.component.ts` was already PrimeNG-compliant before Plan 3 (used mee-card)
- svc-category tree exists at `backend/services/svc-category/` — must be kept in parity with monolith backend
- 7 other svc trees still have old 2-segment rate_limit ID — tracked as FOLLOW-UP-W1a, not blocking

---

## Next actions (as of session start, Plan 4 in-flight)

1. Plan 4 FE coordinator spec → specialist build → FE coordinator gate → squash to integration
2. Plan 1 FE coordinator spec → specialist build → FE coordinator gate → squash to integration
3. Plan 2-W2 FE coordinator spec → specialist build → FE coordinator gate → squash to integration
4. After all groups merged + integration CI green: open feature/section-2/integration → develop PR (merge-commit), hand to founder

---

## Escalation items

- **Build check caveat**: Plan 3 and Plan 4 builds cannot be verified in the section-2-frontend worktree (no node_modules). Founder must run `ng build mfe-catalog` from the master tree on feature/section-2/integration before the integration→develop PR merge.
- **FOLLOW-UP-W1a**: 7 other svc trees have old 2-segment `rate_limit.exceeded` validation_message_id. Not in scope for section-2. Needs a future infra-coordinator sweep.
- **DP-1 (naming)**: `rate_limit.window.exceeded` chosen as generic 3-segment ID (not smart_picker-scoped). FE lead confirmed via frontend-coordinator memory.
