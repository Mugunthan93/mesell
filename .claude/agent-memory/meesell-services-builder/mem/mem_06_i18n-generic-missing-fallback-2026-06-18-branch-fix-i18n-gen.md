## i18n generic-missing fallback (2026-06-18, branch fix/i18n-generic-missing, PR #280, worktree /private/tmp/mesell-wt/i18n-missing off develop@0087562)

### Root cause + fix (NO code change — catalog keys only)
Required-field 422s rendered BLANK. core/errors.py:179 builds the per-field id `validation.{field}.{constraint}`
from the raw Pydantic-v2 error `type` string (missing required field → type="missing"). resolver.py Step-2b
(L112-122) ALREADY rewrites any `validation.{field}.{rule}` → `validation.generic.{rule}` and returns it if present
(resolved tier — no missing_key counter bump, no WARN). The generic key for the `missing` rule (and 9 Pydantic-native
siblings) was simply ABSENT, so it fell through to verbatim-id return = blank UI. FIX = add the keys; the resolver
needs no edit. This is the 4th key in this blank-error class (after q.missing / auth.token_missing / size_in_ltrs.invalid_enum_value).

### Keys added to messages_en.py §5A.I generic block (after validation.generic.invalid_url)
10 keys, all 3-segment `validation.generic.<rule>` (Contract-10 clean): missing, string_too_short, string_too_long,
int_parsing, float_parsing, string_type, greater_than_equal, less_than_equal, greater_than, less_than. These are the
raw Pydantic-v2 `type` strings (NOT the §11/§10 bespoke names like too_short). DO NOT add 2-segment keys. The bespoke
`.missing` keys (validation.q.missing, catalog.draft.missing, pricing.commission.missing, export.front_image.missing,
auth.token.missing) keep resolving at Step-2 unchanged — generic.missing never diverts them (Step-2 wins before Step-2b).
auth.token_missing (2-segment, L_iam_1 deferred) untouched — Step-2b only fires for `validation.*` ids.

### Pydantic-v2 type→generic mapping reference (for future blank-error triage)
required field absent → "missing"; str len → "string_too_short"/"string_too_long"; int/float coerce →
"int_parsing"/"float_parsing"; wrong str type → "string_type"; numeric bounds → "greater_than[_equal]"/"less_than[_equal]".
The enum/url/too_long/invalid_type ones pre-existed. If a NEW blank-error class shows up, grep the Pydantic `type`
string from the raised id's last segment and add `validation.generic.<that>` — never touch resolver.py.

### Verify recipe (held: worktree has no .venv)
Toolchain = master 3.11 venv `/Users/mugunthansrinivasan/Project/mesell/backend/.venv/bin/python3.11` against worktree.
Pass dummy required env as EXPLICIT exports (one-line `env VAR=val` form choked on `GCS_CREDENTIALS_JSON={}` → use
multi-line backslash exports). `pytest tests/test_i18n_generic_fallback.py tests/test_resolver_fallback.py
tests/test_section2_i18n_contract.py` = 61 passed. test_section2_i18n_contract::test_all_registry_keys_are_three_segment
IS the Contract-10 gate (runs locally, not just CI). STATUS_BACKEND.md updated in MASTER tree (NOT in the PR commit) to
keep production diff = messages_en.py + test file only.

---
