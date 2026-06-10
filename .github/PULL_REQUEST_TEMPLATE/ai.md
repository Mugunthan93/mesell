## Summary
One sentence: what does this PR do and why.

## Linked feature / spec
- Feature slug: `<smart-picker>`
- V1_FEATURE_SPEC.md section: `<§F2>`
- BACKEND_ARCHITECTURE.md section (AI Ops): `<§6A>`

## What changed
- File-level bullet list. Use `<path/to/file>` formatting.
- One bullet per concern, not per file.

## Test evidence
- Unit test results (paste `pytest -m "unit"` summary for `tests/ai_ops/` or `tests/eval/`).
- Smoke results (paste `pytest -m "smoke"` summary).
- Lint results (`make lint` summary).
- Screenshot / log paste for any visual or runtime change.

## Reviewer reminder

**Reviewer rule (locked 2026-06-10):**
- For `feature/{name}/{group}` → `feature/{name}` PRs: the lead agent for this group is the reviewer.
- For `feature/{name}` → `develop` PRs: the founder is the reviewer.

## Session
- Session name: `mesell-<feature>-ai-session-<N>`
- Branch name: `feature/<feature>/ai`
- Lead: `meesell-ai-coordinator` (the one who will approve this PR)

## Checklist
- [ ] Branch is `feature/{name}/ai` and is rebased on `feature/{name}` tip
- [ ] CI gates 1+2+3 green (unit, smoke, lint)
- [ ] `feature_board.md` updated to IN REVIEW
- [ ] Agent memory updated with session learnings

---

## AI-specific evidence

### Prompt(s) touched
- Workload(s): `smart_picker` / `autofill` / `watermark`
- Prompt registry version bumped: `<old_version>` → `<new_version>` (e.g., `v1` → `v2`)
- File: `backend/app/ai_ops/prompts/<workload>_<version>.py`

### Eval evidence (MUST be green to merge)
- `smart_picker` golden set: top-5 recall = `<XX>`% (target ≥ 80%)
- `autofill` golden set: invalid-enum rate = `<X>`% (target = 0%)
- `watermark` golden set: accuracy = `<XX>`% (target ≥ 85%)
- Eval command: `pytest tests/eval/<workload>/`

### Cost analysis
- Per-call cost on the new prompt: ₹`<X.XX>` (target ≤ ₹0.05 per MVP_ARCH §8.2)
- Daily projected spend at current QPS: ₹`<XX>` (₹500 hard cap per BACKEND_ARCHITECTURE.md §6A.F)
- LangFuse trace sample link: `<paste>`

### Guardrail compliance
- [ ] Layer 1 prompt-prefix constraint preserved
- [ ] Layer 2 enum re-validation passes for the new prompt
- [ ] Layer 3 (Export Adapter) untouched OR change coordinated with backend lead

### CI gates relevant to this PR
- gate-1 unit · ai_eval (nightly job — must be green within last 24 h)

---

## Acceptance gate (Step 1: feature/{name}/{group} → feature/{name})

- [ ] Branch name follows `feature/{name}/{group}` convention
- [ ] Branch rebased on current `feature/{name}` tip (no merge commits)
- [ ] CI gates 1+2+3 green (unit, smoke, lint) — gates 4+5 advisory at Step 1
- [ ] Group's PR template (this file) filled completely
- [ ] `docs/status/feature_board_<group>.md` row status = IN REVIEW
- [ ] Specialist's agent memory updated with session-close entry
- [ ] Acceptance criteria from `docs/V1_FEATURE_SPEC.md` met for this group's slice
