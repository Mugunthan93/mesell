## Summary
One sentence: what does this PR do and why.

## Linked feature / spec
- Feature slug: `<auth-otp>`
- V1_FEATURE_SPEC.md section: `<§F1>`
- BACKEND_ARCHITECTURE.md section: `<§7>`

## What changed
- File-level bullet list. Use `<path/to/file>` formatting.
- One bullet per concern, not per file.

## Test evidence
- Unit test results (paste `pytest -m "unit"` summary).
- Smoke results (paste `pytest -m "smoke"` summary).
- Lint results (`make lint` summary).
- Screenshot / log paste for any visual or runtime change.

## Reviewer reminder

**Reviewer rule (locked 2026-06-10):**
- For `feature/{name}/{group}` → `feature/{name}` PRs: the lead agent for this group is the reviewer.
- For `feature/{name}` → `develop` PRs: the founder is the reviewer.

## Session
- Session name: `mesell-<feature>-backend-session-<N>`
- Branch name: `feature/<feature>/backend`
- Lead: `meesell-backend-coordinator` (the one who will approve this PR)

## Checklist
- [ ] Branch is `feature/{name}/backend` and is rebased on `feature/{name}` tip
- [ ] CI gates 1+2+3 green (unit, smoke, lint)
- [ ] `feature_board.md` updated to IN REVIEW
- [ ] Agent memory updated with session learnings

---

## Backend-specific evidence

### Database migration
- [ ] Migration authored under `backend/alembic/versions/`
- Revision: `<slug>` (e.g., `f31c75438e61`)
- Down-revision: `<parent_slug>`
- Upgrade tested locally: `✅` / N/A
- Downgrade tested locally: `✅` / N/A (note if irreversible and why)
- Alembic head divergence check between dev and staging: `✅`

### Module(s) touched
- [ ] List each `app/modules/<module>/` subtree touched.
- [ ] Import-linter rules updated if a new cross-module call landed (BACKEND_ARCHITECTURE.md §16).
- [ ] §2.D cross-module matrix still holds (no new ✗ → ✓ without an architecture amendment).

### Contract changes (alerts FRONTEND + AI)
- [ ] New / changed endpoint shape documented in commit body
- [ ] If endpoint added: counted toward §17 endpoint inventory (currently 28 mounted)
- [ ] OpenAPI regenerated and reviewed

### Integration test
- Integration test file: `backend/tests/test_<feature>_integration.py`
- Result: pasted in "Test evidence"

### CI gates relevant to this PR
- gate-1 unit · gate-2 smoke · gate-3 lint · gate-4 integration · gate-5 golden_roundtrip (if XLSX touched)

---

## Acceptance gate (Step 1: feature/{name}/{group} → feature/{name})

- [ ] Branch name follows `feature/{name}/{group}` convention
- [ ] Branch rebased on current `feature/{name}` tip (no merge commits)
- [ ] CI gates 1+2+3 green (unit, smoke, lint) — gates 4+5 advisory at Step 1
- [ ] Group's PR template (this file) filled completely
- [ ] `docs/status/feature_board_<group>.md` row status = IN REVIEW
- [ ] Specialist's agent memory updated with session-close entry
- [ ] Acceptance criteria from `docs/V1_FEATURE_SPEC.md` met for this group's slice
