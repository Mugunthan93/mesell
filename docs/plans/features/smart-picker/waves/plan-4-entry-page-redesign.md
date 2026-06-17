# Plan 4 — Smart Picker Entry Page Redesign

**Status:** IN PROGRESS (FE lane, wave 2 in serialization order: after Plan 3 ✓)
**Type:** FE-only
**Branch:** feature/section-2/frontend
**Specialists:** meesell-angular-component-builder, meesell-angular-ui-styler (if new wrappers needed)

---

## Scope

Redesign the Smart Picker page from a reactive-auto-fire widget into a Claude/ChatGPT-style conversational entry page. This is a FULL LAYOUT REDESIGN (unlike Plan 3 which was layout-freeze).

---

## Locked decisions (founder-approved 2026-06-15)

| Decision | Value | Notes |
|---|---|---|
| Trigger model | Submit on Enter / Send button click | LOCKED — replaces auto-fire 400ms debounce |
| AI call frequency | One call per submit | No auto-fire during typing |
| Refine pattern | Refine-and-resend (edit description → submit again) | Each submit is a fresh AI call |
| Entry page style | Claude.ai / ChatGPT style | Centered, prominent textarea, send button |

---

## What changes (FE only)

### Remove / replace

1. **Remove the reactive auto-fire pipeline**: the current `fromEvent(input).pipe(debounceTime(400), distinctUntilChanged(), filter(valid))` subscription. Replace with an explicit submit handler.
2. **Remove the 400ms debounce** — typing does NOT trigger AI calls.

### Add / redesign

1. **Submit handler**: `onSubmit()` — validates the input (length 1–500), then calls `categoryService.suggest(description)`, updates signals, handles loading/error states.
2. **Enter-key binding**: the `<mee-textarea>` should trigger `onSubmit()` on Enter (without Shift). Shift+Enter inserts a newline (standard conversational UX).
3. **Send button**: a `<mee-button variant="primary" icon="pi pi-send">` (or equivalent send icon) positioned to the right of or below the textarea, triggering `onSubmit()`.
4. **Layout**: Claude-style centered layout — logo/title at top, large prominent textarea in the center, send button, results below. Mobile-first (Tirupur sellers on mobile).
5. **Results display**: keep the top-3-of-5 card rendering (from existing logic), but display below the input area (conversational flow: input → results → refine).
6. **Refine-and-resend**: user can edit the textarea after seeing results and submit again. The results area updates with the new AI response (no persistent session — each submit is stateless from the backend's perspective).
7. **Fallback CTA**: when `fallback_offered: true` — show a banner with the fallback copy (from Plan 2-W2 contract) and a "Browse categories" button.

### Do NOT change

- `category.service.ts` — service methods are unchanged
- `category-card.component.ts` — card component unchanged
- `onBrowse()` handler — unchanged
- Route (`/catalogs/new` → SmartPickerComponent) — unchanged
- `mee-button` import added in Plan 3 — keep it

---

## Acceptance criteria (functional)

- User lands on `/catalogs/new` and sees a centered entry page.
- Typing in the textarea does NOT trigger an AI call.
- Pressing Enter (without Shift) OR clicking the Send button triggers `suggest()`.
- A loading state is shown while the AI call is in-flight.
- Results appear below the input as category cards.
- User can edit the textarea and submit again — a new AI call fires, results update.
- Fallback (no results / AI unavailable) shows the correct banner/CTA.

## Acceptance criteria (technical)

- No auto-fire subscription remains (`debounceTime`, `fromEvent` on input removed).
- `ng lint mfe-catalog` zero errors.
- Zero direct primeng imports in smart-picker files.
- `ng build mfe-catalog` zero errors (coordinate with environment fix needed from Plan 3's gate note).

---

## Serialization constraint

Runs AFTER Plan 3 is squashed to integration (DONE ✓). Plan 1 and Plan 2-W2 wait for this plan to merge to integration.
