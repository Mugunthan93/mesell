### §19.D test-marker classification (PR #85 — MERGE-GATE STEP 3, 2026-06-11)
- [In-file session entry below] — Rule-7 step 3 gate. Verdict APPROVE-WITH-GATE-FIXES. Key LESSONS:
  (1) A `pytestmark = pytest.mark.X` module default is ADDITIVE — you cannot subtract it per-test; to
  exclude a real-infra test from `-m unit`, the module default must be removed and EVERY test marked
  explicitly. This is the trap that left test_shared_database's real-PG tests double-marked `unit`+`integration`.
  (2) A test that imports a vendor lib (openpyxl) INSIDE the test body to assert output is STILL `unit`
  if it uses no real infra — but the import failing in CI is a signal to check whether the PRODUCTION
  code depends on that lib and whether requirements.txt covers it. Here it surfaced a genuine prod-dep gap.
  (3) The modular-monolith rebuild left STALE-API tests (app.config→app.shared.config, cors_origin_list/
  CORS_ORIGINS→CORS_ALLOWED_ORIGINS field, async_session_maker→AsyncSessionLocal) that only surfaced
  once the pythonpath fix let them collect+run. These are test-LOGIC defects, but tiny symbol renames —
  I authorized them as lead-scoped gate exceptions (isolated commits for audit) rather than blocking a
  clean marker PR or shipping a separate round-trip. Reviewed my own diffs transparently in PR comments.
  (4) Gate-4 selection-clean + runtime-fail = infra's lane, not the marker PR's. The discriminator is
  "collection/import errors (mine) vs runtime DB/logic errors (theirs)". `839 / 647 deselected / 192
  selected, zero collection errors` is the proof the markers are right.
