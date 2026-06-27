## Razorpay PR #323 — Alembic Multi-Head Fix COMPLETE (2026-06-20)

### Scope
Worktree `/tmp/mesell-wt/razorpay-integration`, branch `feature/razorpay`. Task: resolve CI Gate-4 "Multiple head revisions" error by generating and verifying a merge migration.

### Root cause
`git merge origin/develop` (commit 794d4de, PR #323 history) brought in `d4e5f6a7b8c9` (pricing_calcs confirmed-model columns) onto the feature branch which already had `f8fa7a36383f` (Razorpay billing Wave-1). Both revisions share parent `c2d3e4f5a6b7` (google identity migration), creating a diamond split with 2 heads.

### Full migration chain on feature/razorpay
```
935e55b4852c (baseline 13 tables)
  → a1b2c3d4e5f6 (pg_trgm + GIN indexes)
  → f31c75438e61 (idx_product_drafts_saved_at)
  → b7c2e1a9d3f4 (pricing_calcs forward-estimator additive columns)
  → c2d3e4f5a6b7 (google identity — branchpoint)
  → f8fa7a36383f (Razorpay billing Wave-1)   ← feature/razorpay head
  → d4e5f6a7b8c9 (pricing confirmed-model)   ← develop head (merged in)
  → e9415bdcae20 (MERGE HEAD — this dispatch)
```

### Fix applied
`alembic merge -m "merge razorpay billing + develop heads" d4e5f6a7b8c9 f8fa7a36383f`

Generated: `backend/alembic/versions/e9415bdcae20_merge_razorpay_billing_develop_heads.py`
- `down_revision = ('d4e5f6a7b8c9', 'f8fa7a36383f')` (tuple = both parents)
- empty `upgrade()` + `downgrade()` — correct, no schema ops

### Verification
- `alembic heads` → exactly ONE head: `e9415bdcae20` (mergepoint)
- `alembic upgrade head` on disposable DB `meesell_alembic_merge_test` (localhost:5432) → all 8 revisions applied, final `current` = `e9415bdcae20 (head) (mergepoint)`
- DB confirmed NOT `meesell`: `SELECT current_database()` = `meesell_alembic_merge_test`
- Disposable DB dropped after verification
- dev `meesell` DB: 3772 categories UNCHANGED

### Commit
`669fdc2` on `feature/razorpay`
`fix(db): alembic merge migration to unify Razorpay billing + develop heads (fixes integration-gate upgrade)`
1 file changed, 26 insertions (+)

### Alembic env var gotcha (feature/razorpay variant)
`alembic upgrade head` fails with "required env var(s) empty or unset" because `app/shared/config.py` validates ALL §5.D env vars at import time (pydantic Settings side-effect). Even for a DB-only alembic run, must supply all 16+ env vars as dummy values. Pattern:
```bash
DATABASE_URL="postgresql+asyncpg://meesell:password@localhost:5432/THROWAWAY_DB" \
VALKEY_URL="redis://localhost:6379/0" \
JWT_SECRET="dummy" REFRESH_TOKEN_PEPPER="dummy" MSG91_AUTH_KEY="dummy" \
MSG91_TEMPLATE_ID="dummy" RAZORPAY_KEY_ID="dummy" RAZORPAY_KEY_SECRET="dummy" \
RAZORPAY_WEBHOOK_SECRET="dummy" GEMINI_API_KEY="dummy" GCS_BUCKET="dummy" \
GCS_PROJECT_ID="dummy" LANGFUSE_PUBLIC_KEY="dummy" LANGFUSE_SECRET_KEY="dummy" \
AUDIT_PII_SALT="dummy" CORS_ALLOWED_ORIGINS="http://localhost:4200" \
SECRET_KEY="dummy" \
python3 -m alembic upgrade head
```
Dummy values never used (alembic doesn't connect to Valkey/Gemini/Razorpay); DATABASE_URL is the only one that matters.

### superuser for throwaway DB creation
`mugunthansrinivasan` is the local superuser (role with CreateDB). `postgres` role does not exist. Pattern: `psql -h localhost -p 5432 -U mugunthansrinivasan -d meesell -c "CREATE DATABASE <throwaway> OWNER meesell;"` then drop after.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| Razorpay PR #323 multi-head fix COMPLETE | project | Merge revision e9415bdcae20 unifies f8fa7a36383f (Razorpay) + d4e5f6a7b8c9 (pricing confirmed); commit 669fdc2; verified on disposable DB meesell_alembic_merge_test; single head confirmed; dev DB untouched |
| alembic upgrade env var gotcha (feature/razorpay) | reference | pydantic Settings validates all 16+ §5.D vars at import; must supply dummies even for alembic upgrade; DATABASE_URL is the only one that matters |
| Throwaway DB superuser pattern | reference | Use `mugunthansrinivasan` (local superuser); `postgres` role does not exist on this Homebrew PG install; CREATE DATABASE ... OWNER meesell; always SELECT current_database() to confirm NOT meesell before any alembic op; DROP after |
