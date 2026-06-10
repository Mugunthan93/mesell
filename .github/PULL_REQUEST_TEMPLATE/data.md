## Summary
One sentence: what does this PR do and why.

## Linked feature / spec
- Feature slug: `<xlsx-export>`
- V1_FEATURE_SPEC.md section: `<§F9>`
- MVP_ARCHITECTURE.md / MEESHO_CATEGORY_INTELLIGENCE.md section: `<§12.6>`

## What changed
- File-level bullet list. Use `<path/to/file>` formatting.
- One bullet per concern, not per file.

## Test evidence
- Unit test results (paste `pytest` summary for parser tests).
- Smoke results (paste `pytest -m "smoke"` summary).
- Lint results (`make lint` summary).
- Screenshot / log paste for any visual or runtime change.

## Reviewer reminder

**Reviewer rule (locked 2026-06-10):**
- For `feature/{name}/{group}` → `feature/{name}` PRs: the lead agent for this group is the reviewer.
- For `feature/{name}` → `develop` PRs: the founder is the reviewer.

## Session
- Session name: `mesell-<feature>-data-session-<N>`
- Branch name: `feature/<feature>/data`
- Lead: `meesell-data-engineer` (the one who will approve this PR)

## Checklist
- [ ] Branch is `feature/{name}/data` and is rebased on `feature/{name}` tip
- [ ] CI gates 1+2+3 green (unit, smoke, lint)
- [ ] `feature_board.md` updated to IN REVIEW
- [ ] Agent memory updated with session learnings

---

## Data-specific evidence

### Source change
- [ ] XLSX template touched: `<name + sheet>`
- [ ] Category JSON / seed touched: `<path>`
- [ ] Field alias / enum touched: `<table + count delta>`

### Parser / scraper evidence
- Run command: `python scripts/<parser>.py --input <X>`
- Output stats: `<X>` rows parsed, `<Y>` warnings, `<Z>` errors
- Diff vs previous run: `<delta>` rows changed

### Schema impact (alerts BACKEND)
- [ ] No schema change — pure data
- [ ] Schema change — Alembic migration coordinated with backend lead

### MVP_ARCHITECTURE.md / MEESHO_CATEGORY_INTELLIGENCE.md amendment
- [ ] Doc amendment included in this PR (preferred)
- [ ] Doc amendment deferred to follow-up PR (justified)

### CI gates relevant to this PR
- gate-1 unit (parser tests) · gate-5 golden_roundtrip (if XLSX touched)

---

## Acceptance gate (Step 1: feature/{name}/{group} → feature/{name})

- [ ] Branch name follows `feature/{name}/{group}` convention
- [ ] Branch rebased on current `feature/{name}` tip (no merge commits)
- [ ] CI gates 1+2+3 green (unit, smoke, lint) — gates 4+5 advisory at Step 1
- [ ] Group's PR template (this file) filled completely
- [ ] `docs/status/feature_board_<group>.md` row status = IN REVIEW
- [ ] Specialist's agent memory updated with session-close entry
- [ ] Acceptance criteria from `docs/V1_FEATURE_SPEC.md` met for this group's slice
