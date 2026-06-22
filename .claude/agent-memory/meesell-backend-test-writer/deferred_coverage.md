# Deferred backend coverage

Test cases consciously deferred, with the reason, so the coordinator can re-spec
them in a later wave. Deferring is allowed; silently dropping coverage is not.

| Item | Wave deferred | Reason | Re-spec when |
|---|---|---|---|
| _(none yet — bootstrapped 2026-06-22)_ | | | |
| P1.11 export-ZIP member-structure | 1 (deferred to Wave 2) | `test_export_zip_member_structure.py` self-skips — ZIP member layout not assertable against the current export path | Wave 2: re-spec as `POST /exports?format=zip` with `GCSAdapter` mocked |
