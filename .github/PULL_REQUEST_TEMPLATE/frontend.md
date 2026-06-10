## Summary
One sentence: what does this PR do and why.

## Linked feature / spec
- Feature slug: `<auth-otp>`
- V1_FEATURE_SPEC.md section: `<§F1>`
- FRONTEND_ARCHITECTURE.md section: `<§7>`

## What changed
- File-level bullet list. Use `<path/to/file>` formatting.
- One bullet per concern, not per file.

## Test evidence
- Unit test results (paste `ng test` output).
- Smoke results (paste `ng test --include=**/*.smoke.spec.ts` summary).
- Lint results (`pnpm lint` summary).
- Screenshot / log paste for any visual or runtime change.

## Reviewer reminder

**Reviewer rule (locked 2026-06-10):**
- For `feature/{name}/{group}` → `feature/{name}` PRs: the lead agent for this group is the reviewer.
- For `feature/{name}` → `develop` PRs: the founder is the reviewer.

## Session
- Session name: `mesell-<feature>-frontend-session-<N>`
- Branch name: `feature/<feature>/frontend`
- Lead: `meesell-frontend-coordinator` (the one who will approve this PR)

## Checklist
- [ ] Branch is `feature/{name}/frontend` and is rebased on `feature/{name}` tip
- [ ] CI gates 1+2+3 green (unit, smoke, lint)
- [ ] `feature_board.md` updated to IN REVIEW
- [ ] Agent memory updated with session learnings

---

## Frontend-specific evidence

### Components / pages touched
- [ ] List each `frontend/src/app/<area>/` subtree touched.
- [ ] PrimeNG imports remain inside `src/app/ui/` (architecture boundary — see FRONTEND_ARCHITECTURE.md).

### Layer architecture compliance
- [ ] Layer 1 (design-system) untouched OR token addition documented
- [ ] Layer 2 (ui kit) untouched OR new `mee-*` primitive added with tests
- [ ] Layer 3 (shared composites) untouched OR new composite documented
- [ ] Layer 4 (features) is the typical landing zone — confirm

### Build evidence
- `pnpm build` succeeded in `<X>` seconds (target: < 90 s per CLAUDE.md Decision 12)
- Bundle size delta: `<+/- KB>` (paste relevant `stats.json` excerpt)

### Routes
- [ ] New / changed routes registered in `app.routes.ts`
- [ ] Auth guard correctly applied (or correctly not applied for public)

### Visual evidence
- Screenshot at 360 px width: `<attach>`
- Screenshot at 1280 px width: `<attach>`

### Accessibility
- [ ] Keyboard nav works on new interactive elements
- [ ] Color contrast checked on new color usage
- [ ] aria-* attributes added where appropriate

### CI gates relevant to this PR
- gate-1 unit (frontend tests) · gate-3 lint (`ng lint`) · build-frontend

---

## Acceptance gate (Step 1: feature/{name}/{group} → feature/{name})

- [ ] Branch name follows `feature/{name}/{group}` convention
- [ ] Branch rebased on current `feature/{name}` tip (no merge commits)
- [ ] CI gates 1+2+3 green (unit, smoke, lint) — gates 4+5 advisory at Step 1
- [ ] Group's PR template (this file) filled completely
- [ ] `docs/status/feature_board_<group>.md` row status = IN REVIEW
- [ ] Specialist's agent memory updated with session-close entry
- [ ] Acceptance criteria from `docs/V1_FEATURE_SPEC.md` met for this group's slice
