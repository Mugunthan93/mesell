# Backend test files authored

Ledger of every pytest file written: path, wave, feature slug, and the route(s) /
module it covers. Append after each task so the coordinator can see coverage
accrue and avoid re-specifying covered ground.

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| _(none yet — bootstrapped 2026-06-22)_ | | | |

## Wave-1 ledger (2026-06-22, PR #380)

Run result for the wave: **1314 passed / 28 skipped / 0 failed**.

New test files authored:

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| `backend/tests/integration/test_iam_otp_rate_limit.py` | 1 | qa-wave-1 | iam — OTP send rate-limit (sliding window, Valkey-backed) |
| `backend/tests/.../test_autofill_shape_idempotent.py` | 1 | qa-wave-1 | catalog/ai — autofill response shape + idempotency |
| `backend/tests/.../test_export_zip_member_structure.py` | 1 | qa-wave-1 | export — ZIP member structure (**self-skip**, see deferred_coverage.md P1.11) |

Extended (added cases to) existing files:

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| `test_google_auth_integration` | 1 | qa-wave-1 | iam — google-auth verify / auto-link |
| `test_settlement_formula` | 1 | qa-wave-1 | pricing — settlement formula |
| `test_razorpay_webhook_router` | 1 | qa-wave-1 | payments — Razorpay webhook routing |
| `test_ai_ops_budget_cap` | 1 | qa-wave-1 | ai_ops — budget cap enforcement |
| `test_suggest_unit` | 1 | qa-wave-1 | catalog/ai — category suggest (unit) |
| `test_catalog_enum_validation_regression` | 1 | qa-wave-1 | catalog — enum validation regression (size_in_ltrs class) |

## Wave-3 ledger (2026-06-22, PR #396 — scribed by meesell-qa-coordinator, write-protection workaround)

Run result for the wave: **59 passed / 0 failed** (scoped, the 5 files); broader
catalog+image+eval suite **122 passed / 2 pre-existing Valkey-6381 infra failures**
(`test_flag_gate.py` — byte-identical at the integration base, NOT introduced).
Gate (qa-coordinator) independently re-ran the 5 files vs `meesell_test`: 59 passed / 0 failed.
Squash-merged to `feature/qa-wave-3/integration` @ `edb875f`.

New test files authored:

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| `backend/tests/modules/catalog/test_live_preview_route.py` | 3 | qa-wave-3 | catalog — `GET /products/{id}/preview` (W3-BE-1,2,3,5): happy 200+locked-shape, cross-tenant 404, unauth 401, autosave-reflect |
| `backend/tests/modules/catalog/test_catalog_delete_route.py` | 3 | qa-wave-3 | catalog — `DELETE /products/{id}` (W3-BE-15a,15b): owner 204 + re-GET 404; cross-tenant 404 non-empty detail |
| `backend/tests/modules/image/test_pil_check_boundaries.py` | 3 | qa-wave-3 | image — PIL checks (W3-BE-7,8,9): CMYK/RGB color space, resolution >=1500x1500 pass+fail, white-BG threshold pass+fail |
| `backend/tests/eval/watermark/test_watermark_asserting.py` | 3 | qa-wave-3 | image/eval — watermark (W3-BE-10): per-fixture flag + aggregate >=85% accuracy threshold (replaces non-asserting run script) |

Rewritten files (carry-forward resolved):

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| `backend/tests/integration/test_export_zip_member_structure.py` | 3 | qa-wave-3 | export — ZIP member structure (W3-BE-6a,6b,6c): **un-skips** the Wave-1 P1.11 self-skip; asserts XLSX/ZIP member names against the correct `_write_xlsx(XlsxRowSpec)` / `_package_images_zip()` signatures; GCS mocked |

Confirm-only (no new tests, covered): W3-BE-12 (`test_catalog_enum_validation_regression.py`), W3-BE-13 (`test_i18n_generic_fallback.py`), W3-BE-14 (suggest GET->405), W3-BE-16 (route-level create happy), W3-BE-17 (price->export roundtrip).
Deferred: W3-BE-11 (cost ceiling) — see deferred_coverage.md.

## Wave A ledger (2026-06-22, PR #432 → feature/qa-pricing/integration)

Run result for the wave files: **36 passed / 0 skipped / 0 failed**.
PQE-BE-02 anchor `TestSettlementFormula::test_real_order` (₹70→₹61.78) PASSED.
PQE-BE-22 `test_pqe_be_22_zip_member_names_are_basenames` now RUNS (not skipped).

New test files authored:

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| `backend/tests/modules/pricing/test_apply_price_route.py` | A | qa-pricing | pricing — apply-price route 204, commission override, ≤0 rejection, cross-tenant 404, flag-OFF 404, get_last_calc, OFFLINE hard rule (PQE-BE-09/15/16/17/18/19/20/21) |
| `backend/tests/modules/export/test_package_images_zip.py` | A | qa-pricing | export — `_package_images_zip` ZIP member basenames, empty refs, download-fail skip (PQE-BE-22/23/24) — Wave-1 P1.11 proper un-skip |
| `backend/tests/modules/export/test_xlsx_round_trip.py` | A | qa-pricing | export — `_write_xlsx` header/value/sanitize, `_round_trip_validate` pass/mismatch, `_value_from_snapshot` precedence (PQE-BE-32/33/34/35/36/42) |
| `backend/tests/modules/catalog/test_quality_gate.py` | A | qa-pricing | catalog — ready-transition 422, enum-422 msg_id, `_compute_completeness` counts, export snapshot status (PQE-BE-44/45/46/47) |

## CAT-BE-17-GUARD — all seeded categories resolve schema (2026-06-22, PR #474 → develop, squash `11da147`)

Closes the spurious category-schema-404 class (QA Wave-1 CAT-E2E-05/06) as an
ENV/seed-state issue, not a data gap. Gate-reviewed by `meesell-qa-coordinator`
(APPROVE) → squash-merged direct to develop (this is a `feature/.../backend → develop`
test PR, NOT a qa-wave integration→develop founder gate).

New test file authored:

| Path | Feature slug | Covers |
|---|---|---|
| `backend/tests/modules/category/test_all_seeded_categories_resolve_schema.py` | fix-category-schema-guard | category — iterates EVERY `categories.id` → `category_service.fetch_schema_dto(category_id, db)` (the real `categories→templates` JOIN, `fetch_schema` + §5A.C DTO projection); collects ALL failures (`CategoryNotFoundError`/empty `fields[]`) then `assert len(failures) == 0`. Honest seed-conditional skip via `_seed_data_absent` (`field_enum_values == 0`) — skips on schema-only `meesell_test`, NEVER false-greens. `@pytest.mark.integration`. |

Run result (gate, this session): on schema-only `meesell_test` (categories=0,
field_enum_values=0) under full CI dummy env → **1 SKIPPED** (BE-SEED-1 reason),
not a false-pass. The seeded green (3,772 categories, 0 failures expected) is OWED
at the next tunnel/CI window — local seeded data lives only in the non-`_test`
`meesell` DB and the `meesell` role lacks CREATEDB to clone a seeded `*_test`.
No real external calls; service-level call so no `_otp_client` event-loop hazard.

LESSON: a guard test that turns an env-dependent runtime 404 into a loud,
bisectable failure on a seeded DB — while honestly skipping (not green-washing)
on an unseeded DB — is the right shape for closing a "seed gap" finding. The skip
predicate must key off a table NO fixture commits to (`field_enum_values`), not a
fixture-polluted one (`categories`).
