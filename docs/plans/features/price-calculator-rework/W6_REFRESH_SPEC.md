# W6 — MONTHLY REFRESH BUILD SPEC (Price Calculator Rework)

| Field | Value |
|---|---|
| Wave | **W6** (binds to W1's path + schema; runs AFTER W1 lands the producer) |
| Section | section-7 (`price-calculator`) — V1 Feature 7 |
| Author | `meesell-data-engineer` (Data Lead) — HYBRID step-1 SPEC |
| Builders (step-2) | `meesell-scraper-maintainer` (census + orchestration glue) + `meesell-database-builder` (transform reuse / drift gate) |
| Merge-gate (step-3) | `meesell-data-engineer` (data-file + refresh-job review) |
| Branch | `feature/section-7/backend` (off `feature/section-7/integration`) |
| Type | code + data |
| Session | `mesell-price-calculator-data-session-15` |
| Authoritative model | `.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md` (confirmed 2026-06-19) |
| Binds to | `docs/plans/features/price-calculator-rework/W1_DATA_SPEC.md` (the producer + schema this refresh reuses) |

> **DO NOT follow** `handoff_pricing_transfer_price.md` (round-4 stale model). The getTransferPrice census is the only source. **Founder ruling 2026-06-19:** ONE monthly run refreshes categories AND pricing — NO separate pricing schedule.

---

## 0. What this wave is (and is NOT)

W1 ships the producer (`build_pricing_lookup.py`), the shipped data file (`meesho_pricing_lookup.json`), and the loader. The census (`meesho_transfer_price_census.py`) and the monthly category scrape (`meesho_batch_scraper.py` via `meesho_scrape_trigger.sh` / launchd) exist today but run **independently and manually**.

**W6 wires them into ONE monthly job:** the same run that refreshes `meesho_category_tree.json` (category discovery + template scrape) ALSO re-runs the getTransferPrice census and regenerates `meesho_pricing_lookup.json` — gated, drift-reviewed, never silently overwritten.

- **NOT** a new schedule, new CronJob, new launchd entry. It extends the existing monthly trigger.
- **NOT** a model change. The math/schema are W1-locked.
- **NOT** a production runtime path. The census runs ONLY in the offline refresh job against the supplier (seller) compute endpoint — NEVER against buyers, NEVER in prod pods.

---

## 1. Integration approach — how pricing folds into the monthly scrape

The monthly scrape is today: discover category tree → scrape XLSX templates (`meesho_batch_scraper.py`). W6 appends a **third stage** to the SAME orchestration, sequenced AFTER the tree is fresh (the census keys on the freshly-refreshed `meesho_category_tree.json` leaf set):

**New orchestrator script (NEW, the single monthly entry):** `backend/scripts/meesho_monthly_refresh.py`

Stages, run in order in one process / one warm login:
1. **Stage A — Category tree + templates** (existing): invoke `meesho_batch_scraper.py`'s `run_all` (which loads/refreshes the tree + downloads templates). Unchanged behavior; reuse as-is.
2. **Stage B — Pricing census** (existing engine, called inline): invoke `meesho_transfer_price_census.py`'s `run()` against the leaf set from the now-current `meesho_category_tree.json`. It is already resumable + paced + sanity-gated; W6 calls it, it does NOT get rewritten. Output: `logs/scraper/transfer_price_census_summary.json` (gitignored).
3. **Stage C — Transform + drift gate** (W1's producer, reused): run `build_pricing_lookup.py` to regenerate the candidate `meesho_pricing_lookup.json`, but route it through the **validation + drift gate** (§3/§4) BEFORE the committed file is touched.

**Session reuse:** Stage A and Stage B share the SAME authenticated WebKit context where feasible (both use the proven `ctx.request.post` Akamai-bypass idiom + the same `supplier-id`/`identifier` headers). The warm `logs/scraper/meesho_storage_state.json` is written by the first stage to log in and reused by the census stage — avoids a second cold login (the OTP trap, see §2). If Stage A finishes and the context is torn down, Stage B re-uses `storage_state` for a warm re-auth.

**The existing trigger** (`meesho_scrape_trigger.sh` + launchd `com.meesell.*`) is repointed from `meesho_batch_scraper.py` to `meesho_monthly_refresh.py`. One schedule, three stages, one warm session.

---

## 2. getTransferPrice call discipline (Stage B)

All already implemented in `meesho_transfer_price_census.py` — W6 must NOT regress these:
- **Read-only compute.** ONE `getTransferPrice` POST per leaf at `price=100`. NO listing, NO image, NO Submit/Publish/Go-Live. The endpoint computes; it does not write.
- **Password-login only / NO OTP.** Reuse the warm `meesho_storage_state.json`. If cold login hits the SMS-OTP wall (observed 2026-06-19), the census halts with `OTP_REQUIRED` rather than blocking — the monthly job is operator-supervisable (founder drops the code, or runs while cookies are warm). Document this in the runbook (§5).
- **Rate limit ~1 req / 2.5s** (`INTER_CALL_SLEEP = 2.5`). ~3,772 calls ≈ 2.6 hr. Acceptable for monthly cadence.
- **Resumable.** The census reads its JSONL and skips done `sscat_ids` — a mid-run abort resumes on re-invoke.
- **Hard-stop on 401/403/429/463** on the `getTransferPrice` endpoint; background SPA XHRs tolerated per the existing `IGNORE_STOP_URL_PATTERNS`.
- **Sanity gate:** `sscat_id 10949 @ price 100 → transfer_price 85.06 ± 0.10` before the census loop runs. Census aborts if the contract drifted.

Contract (refresh-only, NEVER prod): `POST .../singleCatalogUpload/getTransferPrice`, body `{"price":100,"sscat_id":<int>,"supplier_id":<id>,"gst_percentage":null,"duplicate_pid":null,"gst_type":"ENROLMENT"}`, headers `identifier`/`client-type=d-web`/`client-package-version`/`supplier-id`/`content-type`.

---

## 3. Idempotency + validation gate (HARD-FAIL, do not overwrite live)

Stage C MUST NOT overwrite `backend/app/data/meesho_pricing_lookup.json` unless the candidate passes ALL of W1's guardrails (`build_pricing_lookup.py` already asserts these; W6 promotes them to a refresh barrier):
1. **`rows_with_data == 3772`** and **`error_rows == 0`** in the census summary.
2. **`commission_percentage == 0`** for every row.
3. **`formula_ok is True`** for every row.
4. **`len(lookup) == 3772`** and `_meta.total == len(lookup)`.

On ANY violation: the transform raises, the candidate is written to a **side path** (`logs/scraper/meesho_pricing_lookup.candidate.json`, gitignored), the LIVE file is left untouched, and the job exits non-zero with a clear operator message. **A failed monthly refresh degrades to "stale-but-correct" — never to "fresh-but-wrong."**

Idempotency: re-running the whole job with an unchanged Meesho backend produces a byte-identical `meesho_pricing_lookup.json` (W1's `sort_keys=True, indent=2` stable serialization). `_meta.generated_at` is the ONLY field that legitimately changes run-to-run — the drift gate (§4) diffs the `lookup` payload, NOT `_meta`, so a no-change month yields an empty drift report.

---

## 4. Drift detection (review-before-overwrite)

Before promoting the candidate over the committed file, Stage C runs a **drift diff** (new tool, stdlib-only): `backend/scripts/diff_pricing_lookup.py`.

Compares the validated candidate `lookup` vs the committed `backend/app/data/meesho_pricing_lookup.json` `lookup` and emits a human-readable report (`logs/scraper/pricing_lookup_drift_<date>.md`, gitignored) + a machine summary:
- **Added** `sscat_id`s (new categories — expected when Meesho adds leaves).
- **Removed** `sscat_id`s (retired categories — must reconcile against `categories.meesho_leaf_id` so no seeded category is orphaned).
- **Shipping changes:** per `sscat_id`, `old_shipping → new_shipping` with delta and pct.
- **Commission changes:** any row where `commission_percentage != 0` (would be a model-breaking event → STOP, escalate to founder per the model memory's "commission stays a parameter" note).
- **Counts:** added/removed/shipping-changed/unchanged.

**Promotion policy (founder-reviewed):**
- **Zero drift** → promote silently (overwrite committed file, bump `_meta.generated_at`), open the data PR auto-noting "no drift."
- **Drift within thresholds** (configurable: ≤ N added/removed leaves, all shipping deltas explainable) → promote, but the PR body MUST paste the drift report for Data-Lead + founder review at merge-gate.
- **Drift exceeds threshold OR any commission ≠ 0 OR removed leaf still seeded in DB** → **DO NOT promote.** Candidate stays on the side path; the job opens an "Inter-lead requests open" row + a STATUS_DATA blocker; founder reviews the drift before any data file change. This is the same "never silently overwrite" discipline as W1.

The committed file is updated ONLY through the normal data PR flow (squash to `feature/section-7/backend`, Data-Lead merge-gate) — the monthly job stages the change + drift report; a human merges it.

---

## 5. Owners, build slices, file ownership

| Slice | Owner | Files |
|---|---|---|
| **S1 — Monthly orchestrator** | `meesell-scraper-maintainer` | CREATE `backend/scripts/meesho_monthly_refresh.py` (sequences Stage A→B→C, shares warm session, exit codes, runbook docstring). MODIFY `backend/scripts/meesho_scrape_trigger.sh` (repoint to the orchestrator; keep `meesho_batch_scraper.py` runnable standalone). |
| **S2 — Census as callable** | `meesell-scraper-maintainer` | MODIFY `backend/scripts/meesho_transfer_price_census.py` ONLY to expose `run()` cleanly for inline call + accept the warm `storage_state` from Stage A (no model/contract/pacing change). |
| **S3 — Transform gate + drift** | `meesell-database-builder` | CREATE `backend/scripts/diff_pricing_lookup.py`. MODIFY `backend/scripts/build_pricing_lookup.py` (W1's) to add `--candidate-out` side-path mode + return the validation verdict to the orchestrator (keep stdlib-only, keep the W1 hard-fail asserts). Does NOT change the shipped schema. |
| **S4 — Tests** | `meesell-database-builder` | CREATE `backend/tests/scripts/test_pricing_refresh_gate.py` + `test_diff_pricing_lookup.py`. |

**No overlap:** W1 owns the shipped `meesho_pricing_lookup.json` schema, the loader, and the W1 tests — W6 reuses, does not redefine. W2 owns the engine. The ONLY writer of the committed lookup file across W1+W6 is `build_pricing_lookup.py`; W6 never hand-edits it.

**Infra hand-off (cross-lead, data → infra):** the launchd/CronJob *schedule* and any future K8s wiring belong to `meesell-infra-builder`. W6 ships the *job script*; if the schedule artifact (`scripts/launchd/com.meesell.*.plist` or a CronJob) needs editing to point at the orchestrator, open a data→infra memo + an "Inter-lead requests open" board row. For V1 the local launchd repoint is in-scope for the scraper-maintainer per the existing trigger pattern.

---

## 6. Acceptance tests

Gate-1 (unit) MUST be green; gate-5 golden_roundtrip is **N/A** (no XLSX surface touched — justify in PR body).

| Test | Assertion |
|---|---|
| `test_gate_fails_on_short_census` | A fixture census summary with `rows_with_data=3771` → transform raises, live file untouched, candidate on side path. |
| `test_gate_fails_on_nonzero_commission` | One row `commission_percentage=4` → raise, no overwrite. |
| `test_gate_fails_on_formula_not_ok` | One row `formula_ok=false` → raise, no overwrite. |
| `test_gate_passes_clean` | 3772/0-errors/all-zero/all-ok fixture → candidate validated, promotable. |
| `test_idempotent_no_change` | Same census in twice → drift report empty, byte-identical lookup payload (ignoring `_meta.generated_at`). |
| `test_drift_detects_shipping_change` | One row `82→90` → drift report lists `10949: 82→90 (+8)`. |
| `test_drift_detects_added_removed` | Add one `sscat_id`, drop one → report lists 1 added, 1 removed. |
| `test_drift_blocks_removed_seeded_leaf` | A removed `sscat_id` still present in the seed `meesho_leaf_id` set → gate flags BLOCK (no promote). |
| `test_orchestrator_stage_order` | Mocked stages assert A→B→C order and that C aborts if B's summary fails the gate. |

---

## 7. Credentials / secrets / production safety

- Creds live in `.meesho_creds.env` (**gitignored** — confirmed line 8). **ROTATE the credentials exposed in earlier chat sessions** before the next live run (founder action — flag in PR body + STATUS_DATA).
- `logs/` (census JSONL, summary, drift reports, storage_state, candidate side-file) are **gitignored** (`.gitignore` lines 12–15, 26). Only the committed `backend/app/data/meesho_pricing_lookup.json` enters git, via the reviewed data PR.
- Creds are NEVER echoed to logs (existing scripts log `user[:4]` only — preserve this).
- **NEVER in production against buyers.** This is a supplier-side READ-only compute census run by the offline monthly refresh job. It does NOT run in prod pods, does NOT touch buyer flows, creates NO listings, and clicks NO Submit/Publish. The runtime calculator (W2) is fully offline from the shipped lookup file — zero live Meesho calls, zero ban risk.

---

## Return summary (for the dispatcher)

**Integration approach:** new `meesho_monthly_refresh.py` orchestrator sequences three stages in one warm session — (A) existing tree+template scrape, (B) existing getTransferPrice census against the fresh leaf set, (C) W1's `build_pricing_lookup.py` transform — and the existing launchd trigger is repointed to it. One monthly run, categories + pricing together; no new schedule.

**Validation/drift gate:** transform hard-fails (no overwrite of the live file) unless 3,772 rows / 0 errors / all commission=0 / all formula_ok. A `diff_pricing_lookup.py` surfaces added/removed `sscat_ids` + shipping/commission changes into a review report; zero-drift auto-promotes, in-threshold drift promotes with the report pasted for merge-gate review, over-threshold / commission≠0 / removed-but-seeded leaf BLOCKS and escalates to the founder. The committed file changes only through the normal reviewed data PR.

**Build slices + files:** S1 orchestrator + trigger repoint (scraper-maintainer: NEW `meesho_monthly_refresh.py`, MODIFY `meesho_scrape_trigger.sh`); S2 census-as-callable (scraper-maintainer: MODIFY `meesho_transfer_price_census.py`); S3 transform gate + drift (database-builder: NEW `diff_pricing_lookup.py`, MODIFY `build_pricing_lookup.py`); S4 tests (database-builder).

**Acceptance tests:** 9 tests covering hard-fail gates (short census, non-zero commission, formula-not-ok), clean pass, idempotency, drift detection (shipping/added/removed), removed-seeded-leaf block, and orchestrator stage ordering. Gate-1 green, gate-5 N/A.

**Open question:** Drift promotion thresholds — what added/removed-leaf count and shipping-delta magnitude should auto-promote vs require founder review? (Proposed default: auto-promote on zero drift; require review on any drift; hard-block on commission≠0 or a removed-but-still-seeded leaf. Founder to set the numeric thresholds.) Secondary: does the founder want the monthly run supervised (warm cookies / OTP code on hand) or should the job fail-soft and email the operator when cold login hits OTP?
