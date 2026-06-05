# Reference — is_advanced state (as of 2026-06-05)

## What founder said
"`is_advanced` per-field metadata never wired in seed (founder decision §12.4) — most material gap"

## What the code actually says (scripts/build_template_schemas.py)
- Line 83-85: `ADVANCED_CANONICAL_NAMES = {"group_id"}` — explicit allowlist exists
- Line 291: `is_advanced = canonical_name in ADVANCED_CANONICAL_NAMES` — defaults from allowlist
- Line 302-303: `if override.get("is_advanced") is True: is_advanced = True` — override path
- Line 316: emits `"is_advanced": is_advanced` into the schema_jsonb field object
- §5.6.1 schema sample at MVP_ARCHITECTURE line 882 confirms this is the documented contract

## So the gap is narrower than founder's description
The CODE PATH that writes is_advanced into templates.schema_jsonb is functional. The real gaps are:
1. The DB row content has not been verified — seed must be re-run AND the DB inspected to confirm `group_id` field objects across all template rows have `is_advanced: true`. Smoke tests at 40/40 pass don't include this assertion.
2. No override entries in `data/parsed/field_display_overrides.json` mark anything else `is_advanced` — only `group_id` ever gets it. §12.4 phrasing ("Group ID and a small allowlist") implies further entries may be expected; needs founder/data-engineer confirmation on which other canonical names belong.
3. No backend route consumes the flag yet (because routers are being torn down anyway).

## Implication for the gap plan
- This is not "wire is_advanced from scratch"; it is "verify wiring with a DB assertion test + decide whether allowlist needs expansion".
- Acceptance test: `SELECT count(*) FROM templates WHERE schema_jsonb @> '{"fields": [{"canonical_name": "group_id", "is_advanced": true}]}'::jsonb` returns > 0 (and ideally ≈ N templates containing group_id).
- Cheap to close. Bumped from "most material gap" to "verification chore" in the plan.
