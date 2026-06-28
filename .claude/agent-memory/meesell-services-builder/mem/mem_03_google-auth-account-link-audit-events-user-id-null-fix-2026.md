## google-auth account-link audit_events.user_id NULL fix (2026-06-20, branch fix/google-link-audit-userid, worktree /private/tmp/mesell-wt/google-link-audit-fix off develop@fa61a61, PR #324 → develop)

### Bug + fix (relationship-loading directive ONLY — NO DDL, NO migration)
google account-LINK path (existing phone user signs in with Google on matching verified email): audit rows
(auth.login.success + auth.google.linked) INSERT with valid user_id inside the SAVEPOINT, but SQLAlchemy's
unit-of-work then emits `UPDATE audit_events SET user_id=NULL` at the OUTER commit → NotNullViolationError.
Trigger = the bidirectional `back_populates`: on LINK, `by_email` is a session-managed persistent User whose
`audit_events` collection is never appended to, so the UoW nulls the child FK to reconcile the empty collection.
The CREATE-new-user path escapes it. FIX:
- `app/shared/models/user.py` User.audit_events: drop `back_populates="user"`, add `viewonly=True`.
- `app/shared/models/audit_event.py` AuditEvent.user: drop `back_populates="audit_events"` (keep relationship → `relationship("User")`).
GENERAL LESSON: a child table with NOT-NULL parent FK + bidirectional back_populates, where the parent's
collection is loaded-but-not-appended on a mutate path → UoW will null the child FK at commit. `viewonly=True`
on the parent side (and dropping back_populates on both) is the surgical fix. svc-iam vendored copies deliberately
DROP all ORM relationships → never carry this class of bug; NEVER edit them for a monolith relationship fix.

### Test (tests/test_google_auth_integration.py::test_google_links_to_existing_phone_user_by_email)
Removed @pytest.mark.xfail; added crux: query `select(AuditEvent).where(user_id==original_id)`, assert
{auth.login.success, auth.google.linked} ⊆ event_types AND all rows user_id==original_id (non-null). Cleanup:
DELETE audit_events BEFORE the user row (FK is RESTRICT post-fix), else teardown blocks. Added `from sqlalchemy
import delete, select` + AuditEvent import inside the test body.

### Branch topology TRAP (recurring — verify before cutting)
Spec said branch off + target `feature/google-auth`. REALITY (git): that branch was 34 commits BEHIND develop;
its 8 unique commits were already squash-merged to develop as PR #295 (google code e083dff) + PR #322 (iam_client
harness repair 1a45199). Its tip is NOT an ancestor of develop and its test file is the BROKEN PR-#295 version
(`app = client.app`). The #322-repaired test + google service code live on DEVELOP. → branched off develop,
targeted develop, flagged the discrepancy in PR #324 body + STATUS + reported to coordinator. RULE: when a spec
names a feature branch as base/target, FIRST `git rev-list --count <branch>..develop` + check whether the branch
tip is an ancestor of develop + grep the repaired marker (here `iam_client`) — squash-merged feature branches go
STALE and editing them re-introduces the broken file.

### Test harness recipe (reused, works)
Worktree has no .venv. Toolchain = master venv `/Users/.../backend/.venv/bin/python3.11`. Config needs the FULL
§5.D env registry → `set -a; . <master>/backend/.env; set +a` to load dev placeholders, THEN HARD-OVERRIDE
`export TEST_DATABASE_URL=...meesell_test` + `export DATABASE_URL=$TEST_DATABASE_URL` (the .env's DATABASE_URL
points at the protected dev DB `meesell` — MUST override). conftest refuses any DB not ending in `_test`.
Disposable `meesell_test` already exists on localhost:5432 (creds meesell:password); provisioning fixture DROPs
public schema + alembic-upgrades it, gated on TEST_DATABASE_URL. PYTHONPATH=$PWD (worktree backend). ruff at
/opt/homebrew/bin/ruff. git push from worktree needs token URL: `git push https://x-access-token:$(gh auth token)@github.com/...`.
