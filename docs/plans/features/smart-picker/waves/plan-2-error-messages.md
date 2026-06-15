# Plan 2 — Error Message Surfacing

**Status:** W1 DONE ✓ (squash `2766ed7` on integration) · W2 PENDING (FE lane, last in serialization order)
**Type:** Split — W1 BE-only, W2 FE-only
**Branch:** feature/section-2/backend (W1, merged) · feature/section-2/frontend (W2, pending)

---

## Wave 1 (BE) — i18n error message contract  ✓ COMPLETE

**Commit:** 960ed70 on feature/section-2/backend → squashed as 2766ed7 on integration
**Specialist:** meesell-services-builder

### Changes delivered
1. `validation_message_id = "rate_limit.exceeded"` → `"rate_limit.window.exceeded"` in both:
   - `backend/app/core/middleware/rate_limit_mw.py`
   - `backend/services/svc-category/app/core/middleware/rate_limit_mw.py`
   - The `code = "rate_limit.exceeded"` machine slug was left unchanged.
2. Registered `"rate_limit.window.exceeded"` in both `messages_en.py` files.
3. Fixed `validation.suggest_q.too_short_or_long` copy from "2 and 60" to "1 and 500" (matches enforced bound).
4. Updated `backend/tests/test_core_rate_limit_mw.py:66` to match renamed ID.
5. New test: `backend/tests/test_section2_i18n_contract.py` — 10 tests, all pass.

### Locked copy contract (for Plan 2-W2 FE implementation)

| validation_message_id | HTTP status | English copy | FE treatment |
|---|---|---|---|
| `validation.suggest_q.too_short_or_long` | 400 / 422 | "Please enter between 1 and 500 characters to search categories." | Inline below textarea |
| `category.lookup.not_found` | 404 | "We couldn't find that category. Please pick another from the list." | Inline |
| `category.field_enum.not_found` | 404 | "We couldn't load the options for this field. Please refresh the page." | Inline |
| `validation.browse.invalid_pagination` | 400 / 422 | "Page or limit is out of range. Please try a smaller page size." | Inline in browse page |
| `rate_limit.window.exceeded` | 429 | "You've reached the category suggestion limit. Try again in an hour." | mee-toast |
| `smart_picker.ai.unavailable` | **200** (not an error) | "Smart suggestions are unavailable right now — browse categories manually instead." | fallback_offered=true → banner/CTA |
| `smart_picker.budget.exceeded` | **200** (not an error) | "Smart suggestions are taking a break for today — browse categories manually instead." | fallback_offered=true → banner/CTA |

**Key FE rules from contract:**
- 4 domain IDs + 1 rate-limit ID are genuine error envelopes (key on `validation_message_id`).
- AI-unavailable and budget-exhausted are NOT errors — key on `fallback_offered: boolean` in the 200 body.
- 401 → silent logout (per existing category.service.ts pattern).
- 5xx (non-429, non-402) → mee-toast "Something went wrong. Please try again."

### Known follow-up (out of scope for W1)
7 other svc trees still carry the old 2-segment `rate_limit.exceeded` ID. Not blocking — tracked as FOLLOW-UP-W1a. Future infra sweep wave to normalize.

---

## Wave 2 (FE) — Error message surfacing  ⏳ PENDING

**Serialization:** Must run AFTER Plan 1 merges to integration (both touch smart-picker component and browse component).
**Specialists:** meesell-angular-component-builder

### Deliverables

1. **Smart-picker component**: Wire the 7 error scenarios from the locked contract above:
   - Inline `<mee-inline-error>` (or equivalent) below the textarea for validation errors (400/422 suggest_q).
   - `mee-toast` for rate-limit (429) and unexpected 5xx.
   - `fallback_offered: true` branch → show a persistent banner + "Browse categories manually" CTA (navigates to `/categories/browse`).
   - 401 → silent logout (already handled by jwtInterceptor — confirm it still fires).
2. **Browse component**: Wire `validation.browse.invalid_pagination` as inline error on the browse page.
3. All copies MUST match the locked contract table above — no ad-hoc copy.

### Acceptance criteria
- Every error scenario in the table above is surfaced correctly (manual test matrix required).
- `ng lint mfe-catalog` zero errors.
- No hardcoded error strings in the component — all copy comes from the contract table.
