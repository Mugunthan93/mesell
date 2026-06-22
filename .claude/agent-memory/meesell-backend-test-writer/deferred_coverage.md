# Deferred backend coverage

Test cases consciously deferred, with the reason, so the coordinator can re-spec
them in a later wave. Deferring is allowed; silently dropping coverage is not.

| Item | Wave deferred | Reason | Re-spec when |
|---|---|---|---|
| _(none yet — bootstrapped 2026-06-22)_ | | | |
| P1.11 export-ZIP member-structure | 1 (deferred to Wave 2) | `test_export_zip_member_structure.py` self-skips — ZIP member layout not assertable against the current export path | Wave 2: re-spec as `POST /exports?format=zip` with `GCSAdapter` mocked |
| P1.11 export-ZIP member-structure | **RESOLVED in Wave 3** (PR #396) | Rewritten as `test_export_zip_member_structure.py` against the correct `_write_xlsx(XlsxRowSpec)` / `_package_images_zip(image_refs, user_id, db)` signatures; asserts XLSX validity (openpyxl-loadable, Product Name / Brand Name headers + data row) AND ZIP member names == GCS path basenames; GCS mocked at the adapter boundary. No longer self-skips. | — (closed) |
| W3-BE-11 cost ceiling (smart-picker suggest ≤ a per-call rupee ceiling) | 3 (deferred) | Gated on a founder-confirmed number — master-memory finding-8 shows smart_picker ~₹0.09–0.20/call vs the ≤₹0.05 design ceiling; the founder DEFERRED the ceiling to the staging/eval phase. Cannot write the assertion honestly without a confirmed ceiling or live GEMINI cost data. | When the founder confirms a relaxed ceiling OR live GEMINI cost telemetry is available at staging/eval |
