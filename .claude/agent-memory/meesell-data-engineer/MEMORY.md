# Memory — meesell-data-engineer

## Agent Identity
Data engineer coordinator for MeeSell. Orchestrates the 2 data specialists (xlsx-parser, scraper-maintainer). Owns STATUS_DATA.md, schema versioning of derived JSON, refresh cadence, coverage stats. Brand-master deferred to V1.5. Decentralized memory ecosystem.

## Notes & Learnings

### 2026-06-04 — Founder's batch workflow preference (LOCKED)
**Rule:** Full-corpus parse, batch by batch (12 batches), not random sampling. Each batch ends with a founder discussion BEFORE the next batch dispatches.

**Why:** Founder wants to see how diverse the 3,772 categories actually are before MVP design. Discussion-per-batch lets him shape the MVP iteratively.

**How to apply:**
- Specialist produces RAW findings only — never auto-appends to the SSoT
- Coordinator + founder manually integrate accepted findings into `docs/MEESHO_CATEGORY_INTELLIGENCE.md`
- After all 12 batches complete → SSoT drives MVP design (`docs/MVP_ARCHITECTURE.md`)
- 12-batch plan documented in STATUS_DATA.md current phase

### 2026-06-04 — Workspace hook conflict + one-time fallback pattern
**Rule:** When the workspace agent-routing hook blocks dispatching `meesell-*` agents (forces `nexus:level-*`) AND the founder cannot immediately fix the hook, the authorized fallback is:
- Dispatch `nexus:level-3:python-developer-agent` with the full `meesell-*` spec content embedded in the prompt
- Route ALL memory writes to the real `meesell-<role>/MEMORY.md` (NOT the nexus agent's own memory)
- Have the nexus agent prepend an ATTRIBUTION NOTE to the meesell agent's memory so continuity is preserved AND the fallback is visible
- Schedule a reminder to fix the hook properly before the next dispatch

**Why:** Founder mandate is "only `meesell-*` agents handle MeeSell work" (CLAUDE.md Stage 2). The workspace hook contradicts that. Fallback preserves architecture integrity (memory continuity) while keeping work moving.

**How to apply:** This is NOT a precedent. Use only when founder explicitly authorizes it ("go" / "ok") for a single dispatch. Hook must be fixed before any subsequent batch.

### 2026-06-04 — SSoT integration is manual, never automated
**Rule:** `docs/MEESHO_CATEGORY_INTELLIGENCE.md` is the single source of truth. It is integrated MANUALLY by coordinator + founder after discussing each batch's draft findings. Specialists never write to it directly.

**Why:** Founder explicitly said "dnt append the summary we need to discuss about it and intehrate it correctly" — wants editorial control over what becomes truth.

**How to apply:** Every batch dispatch prompt must explicitly forbid the specialist from creating/editing the SSoT. Specialist writes a DRAFT file (e.g. `data/parsed/batch_NN_summary.md`); coordinator + founder review together; coordinator (with founder direction) writes the SSoT.

### 2026-06-04 — TWO-SECTION DATA MODEL (founder-locked, FOUNDATIONAL)
**Rule:** Every parsed field is classified into one of two buckets:
1. **Onboarding inputs** — collected ONCE on the seller profile, auto-filled into every catalog form
2. **Catalog wizard inputs** — collected PER PRODUCT in the wizard

**Why:** Founder's instinct after seeing Batch 1: the 9-field compliance block (Manufacturer/Packer/Importer × Name/Address/Pincode) is the same for every product. Multiplying that across N products is pure waste. Same logic applies to any seller-constant field.

**How to apply:**
- Every batch's draft summary classifies each field as `onboarding | catalog | tbd`
- Onboarding fields go into `seller_profile` schema (backend) and onboarding wizard (frontend)
- Catalog fields go into `categories.attributes_jsonb` (backend) and the per-category wizard (frontend)
- Batch 1's identified onboarding fields: 9 compliance fields + Country of Origin (10 total, all seller-constant)
- More onboarding fields may surface in Batches 2-12 — keep the classification rule list open

### 2026-06-04 — Six locked MVP decisions from Batch 1 review
**Decisions locked by founder after reading batch_01_summary.md:**

1. **Seller profile auto-fills compliance block.** Block listing until profile complete.
2. **Brand picker = autocomplete + API search**. Same pattern will apply to other "field name same, enum differs by category" cases revealed in Batches 2-12. Brand is the first instance — collect more before generalizing.
3. **Two-tier form (Compulsory / Optional) for V1.** Add Recommended tier only if Batches 2-12 prove it exists.
4. **AI auto-fill is P0 — but ONLY suggests values from validated enum lists.** No free-text hallucination. Show source/confidence. AI never invents data.
5. **Wizard is data-driven, not hardcoded step count.** Step boundaries emerge from the field-schema structure. Build for evolution across Batches 2-12.
6. **Input primitive LIBRARY, not just a searchable picker.** Primitives needed (Batch 1 evidence): short text, long text/textarea, number, currency-number (₹), weight/unit-number, small dropdown (<20), medium searchable dropdown (20–500), large API-backed search (Brand, 500+), date picker, image upload, address-group bundle. Each catalogued during parsing so frontend can render mechanically.
7. **Backend stores schema by TEMPLATE, not by leaf.** Batch 1 proved 169 unique templates serve 179 leaves. `categories.attributes_jsonb` keyed by template-hash; leaves map many-to-one to templates. Saves storage + avoids drift between near-duplicate categories.
8. **Smart Category Picker returns TOP-5 + "browse manually" fallback** (not top-3). Women Fashion has near-duplicate categories (Kurtis / Kurti With Bottomwear / Suits) where Gemini disambiguation from a one-line description is shaky. Top-5 + manual escape hatch is the safer default for V1.

### 2026-06-04 evening — Six MVP-architecture follow-ups locked by founder
After full-corpus parse + MVP architecture draft, founder answered all 6 open questions:

9. **Books ISBN = follow Meesho (optional).** Do not enforce stricter than Meesho. Reduces friction for casual book sellers.

10. **Meesho source typos = auto-correct internally, restore on XLSX export.** UI displays corrected canonical names ("Primary", "Secondary"). XLSX exporter has a reverse map and emits the typo verbatim when generating Meesho-format files. Field-aliases table needs a `for_xlsx_export` boolean column.

11. **Long-tail super-categories = include all 3,772 in V1.** No filter. Reuses the existing 11 primitives. Adds ~40 leaf rows to seed.

12. **Group ID = show inline as Optional in V1.** No "Advanced" hide pattern. Simpler renderer. Revisit if user testing surfaces confusion.

13. **Warranty = per-product wizard step (match Meesho), NOT an onboarding extension.** Conditional step appears for categories with warranty fields (~190 leaves, Electronics + Appliances + some Cookware). compliance_extensions map does NOT include warranty.

14. **Eye-Serum collapsed compliance = store BOTH representations, render per category.** seller_profile has 9 standard fields + 3 combined "Details" fields. Backend auto-populates the combined fields on save (concatenating standard fields). Frontend renders per template's `compliance_shape` flag ("standard" or "collapsed"). Founder's exact words: "we need to keep it like how meesho handle it" — be faithful to Meesho's actual templates, don't normalise away their variation.

### 2026-06-04 evening — CORE_PHILOSOPHY.md locked + decisions #12 and #14 revised

Founder locked `docs/CORE_PHILOSOPHY.md` — 10 mandates, 8 forbids, 5 structural patterns. Architecture pattern: seller-facing flexibility + Meesho-faithful export, joined by a single Export Adapter component.

**Revised decisions after philosophy lock:**

12-REVISED. **Group ID = show behind "Advanced fields" toggle in wizard.** NOT default-visible (philosophy rejects "show field without explanation"). NOT fully hidden (founder preserved seller's optional choice). Sits between Pattern 2 (hidden + default-on-export) and a regular optional field. Introduces Pattern 5 (Advanced fields) — opt-in opacity, where seller's choice to expand acknowledges they may not understand the field.

14-REVISED. **Eye-Serum compliance = collect 9 standard fields UNIVERSALLY, Export Adapter concatenates to 3 combined fields ONLY at Eye-Serum XLSX export.** Drops the "store both representations" requirement. seller_profile has only the 9 standard fields. Cleaner internal model. Same Meesho compatibility. Better UX (typing into clearly-labeled inputs beats typing into one mushy "Details" textarea).

**Other locked decisions (1-11, 13) ALIGNED with philosophy as-is** — no revision needed. The philosophy actually strengthens several of them (especially #4 AI guardrail = 3-layer enforcement, #2 Brand picker = Pattern 3 escape-hatched dropdowns).

**Minor extensions to existing decisions (philosophy adds clarity, doesn't revise):**
- #2: Brand picker needs "request to add" workflow (Pattern 3)
- #4: 3-layer enum enforcement (AI prompt + frontend + backend validators)
- #5: Wizard step names are plain English, never generated codes
- #6: 10 primitive components consume display layer inputs (display_label, display_help, validation_message). Never read meesho_column_header.
- #8: Smart Picker shows seller-friendly category paths

**How to apply:**
- Every batch summary maps fields → primitive types
- Backend data model honors onboarding/catalog split
- Frontend builds primitive library first, then composes wizard from per-category schema
- AI prompt-engineer (when activated) must constrain Gemini to enum values where validations exist

### 2026-06-04 — Cross-batch watchpoint: field-name clashes with different enums
**Rule:** Track fields whose `name` is identical across categories but whose `enum_source` (resolved values) differs by category. Brand is the canonical example: same field name, but Sarees has 3,730 brands and Mobile Covers has 2,000+ different brands.

**Why:** These fields can't be modelled with a single global enum. They need backend tables keyed by `(category_id, field_name)` OR a runtime resolver. This shapes the data model.

**How to apply:**
- After each batch, run a "field name → distinct enum sources" analysis
- Maintain a running list in MEMORY of fields where same name = different enums
- Flag these as "API-resolved picker" fields in the input-primitive classification

### 2026-06-04 — All data-layer deliverables complete

`docs/MEESHO_CATEGORY_INTELLIGENCE.md` written and locked. 424 lines, 9 sections, co-authored with founder 2026-06-04.

All data deliverables complete:
- `data/parsed/batch_01` → `batch_12` (raw JSON + summary md, 24 files)
- `data/parsed/FULL_CORPUS_ANALYSIS.md` (12-section synthesis)
- `data/parsed/canonical_field_aliases.json` (16+ alias families)
- `docs/MVP_ARCHITECTURE.md` (2,796 lines, 15 sections, 14 founder decisions)
- `docs/MEESHO_CATEGORY_INTELLIGENCE.md` (SSoT, locked)

BACKEND / FRONTEND / AI sessions are now fully unblocked. Hand-offs documented in STATUS_DATA.md.

### 2026-06-05 — MVP_ARCHITECTURE gap analysis dispatched + delivered
**Output:** `docs/MVP_ARCHITECTURE_GAP_ANALYSIS.md` (~430 LOC, 6 sections, 18 gaps catalogued).

**Trigger:** DATABASE track complete (Phases 0–4 done, Alembic head `935e55b4852c`); database coordinator surfaced 4 schema deltas + 7 starting-list gaps where §2 drifted from §5.5/§5.6/§12. Founder authorized gap-analysis dispatch before API track begins.

**Inventory summary:**
- **Total: 18** gaps — 11 validated from database coordinator's starting list + 7 newly surfaced.
- **Tier-1 BLOCKER-V1: 4** — G1 (§2 DDL stale), G2 (pricing_calcs/exports → legacy V1_FEATURE_SPEC), G8 (15 export adapter golden fixtures unauthored), G16 (CI YAML path-triggers reference non-existent scripts).
- **3 most surprising:** G16 (CI gate doubly hollow — no fixtures AND wrong paths), G11 (`profile_complete` vs `onboarding_complete` — three sources of truth for one column name; DB has the right one only because builder followed SSoT), G13 (cache keyed by template_id in §6.4 but category_id in §6.7).

**Ranking heuristic used:** Tier × Severity × Blast-radius, with Tier-1 reserved for either schema drift live in DB or hollow V1 acceptance gates. Severity = BLOCKER-V1 only when a downstream agent will produce wrong code OR a V1 acceptance criterion has no test. Blast radius weighted highest for "any agent reading this in isolation gets it wrong" issues (G1, G11, G13).

**Systemic drift pattern observed:** every section originally drafted as `docs/draft_architecture_section_N_*.md` (5 files still present in `docs/`) was inserted as Section 8/9/10/11 of MVP_ARCHITECTURE.md without renumbering its draft-internal sub-headers. Root cause of G3 (numbering collision: Section 10 + Section 11 both use §11.x) and G14 (orphan draft files). Discipline rule for future: "promote draft to section → renumber + delete the draft in the same commit."

**Recommended ordering (Phases R1–R5):**
- **R1 (3–4 hr, founder approval)** — backport G1, G2, G11 into §2 DDL. Doc only, no code.
- **R2 (2–3 hr, no approval)** — code-lock step assignment + primitive classifier into `backend/app/i18n/` so quarterly refreshes can't silently drift (G6, G7).
- **R3 (4–6 hr, partial approval)** — fix §8/§9/§10/§11 numbering collision (G3); reconcile primitive count to 10 (G5); pick `category_id` for cache keys (G13); archive 5 orphan draft files (G14); G12 + G18 need founder rulings.
- **R4 (3–4 days, founder co-authors)** — author 15 round-trip fixtures + 50 picker descriptions + 30 autofill specs + 30 watermark images (G8, G9); fix `.gitlab-ci.yml` path-triggers (G16). Parallelisable across 3 specialists.
- **R5 (1 hr for V1)** — TTL on product_drafts via Celery beat (G10); ContextVar hardening deferred to V1.5 (G15).

**Explicit non-proposals (sidebar §5):** no schema migrations, no re-seeding, no new tables, no re-litigating §12 founder decisions, no new agents. All proposed work is doc reconciliation + small code-moves + artifact authoring.

**Disagreements with §12:** none. All §12 founder-locked decisions reaffirmed as correct; drift is documentation-only (§2 wasn't updated when §12 was authored).

**Verdict for founder review:** ready. Recommended dispatch order R1+R3 (parallel) → R2 → R5-G10 → R4. Total V1 effort ~5–6 person-days, half of which is founder-bounded content authoring.

## Session mesell-repo-management-session-1 — Step 5 — Data Engineer spec evolved into Data Lead spec; feature_board_data.md initialised

**Date:** 2026-06-10 (initial creation)
**Branch:** repo-management/foundation (off origin/develop)
**Trigger:** MASTER_PLAN.md ratified APPROVED 2026-06-10. Step 5 of the rollout: rewrite the 5 lead specs.

**Founder decisions locked verbatim:**
- D1 — Merge gate: Lead reviews/merges `feature/{name}/<group>` → `feature/{name}`. Founder reviews/merges `feature/{name}` → `develop`.
- D2 — Board updates: Specialist marks `IN REVIEW` on PR open. Lead marks `MERGED` on PR merge.
- D3 — Spec rewrite: Clean replacement. Slug stays `meesell-data-engineer`. Title and framing change to "Data Lead". "Coordinator" framing in the body is retired.

**Files written:**
- `.claude/agents/meesell-data-engineer.md` — top-to-bottom rewrite (6,268 → 19,212 bytes). Frontmatter slug/model/tools unchanged; description rewritten. Body now leads with Identity-as-Lead, then Owns / Merge gate / Update protocol / Cross-lead coordination / Session naming, then Mandatory First Action (updated read order to include MASTER_PLAN + feature_board_data.md), Decentralized Memory (preserved), Hard Constraints (preserved + 4 new NEVER + 2 new ALWAYS), Project Context (preserved), Specialists you dispatch (new dedicated section), Scope IN/OUT (preserved + merge gate + board), Operating Procedure (preserved + board update steps), Reporting Format (preserved + Session + Board sweep lines), Stop Conditions (preserved + 2 new), Hand-off Protocol (reframed around board).
- `docs/status/feature_board_data.md` — created per MASTER_PLAN §6.2 template. Empty active/recent/inter-lead tables, status vocabulary, brief Acceptance gate note pointing at `.github/PULL_REQUEST_TEMPLATE/data.md`.

**Behavioural change (forward-going):**
- I am now a **lead**, not a coordinator. I approve and merge `feature/{name}/data` → `feature/{name}` PRs in the data domain. I do NOT approve `feature/{name}` → `develop` — that's the founder's gate.
- I am the **sole writer** of `docs/status/feature_board_data.md`. I never touch another lead's board.
- Every specialist dispatch carries the session name `mesell-{feature}-data-session-{N}`.
- Cross-lead coordination uses the memo protocol — write to `.claude/agent-memory/meesell-data-engineer/handoff_<topic>.md`, open an "Inter-lead requests open" row on my own board, 48-hr SLA before founder escalation.
- Board sweeps at session start AND session end. 7+ day untouched rows flagged in Notes and STATUS_DATA.md.

**Pointers:**
- MASTER_PLAN.md §1 (branch model), §2 (merge flow — D1 lives at §2.1/§2.2), §4 (session naming), §5.5 (data PR template), §6 (feature_board.md — D2 lives at §6.5), §7 (lead responsibilities — §7.1 ownership, §7.3 escalation, §7.5 cross-lead).
- Decision D3 explicit at MASTER_PLAN.md "Decisions" table — slug retained, framing replaced.

**Non-impact areas (verified untouched per task constraints):**
- No other `meesell-*.md` agent spec touched.
- No other `feature_board_*.md` touched (only `feature_board_data.md` created).
- No `backend/`, `frontend/`, `k8s/`, `infra/`, `terraform/`, `data/`, `themes/` files touched.
- No commits made.
- No MASTER_PLAN modifications.
- No STATUS_DATA.md modifications (this is repo governance, not a feature chunk — confirmed scope-out).

### 2026-06-10 — Knowledge-sync survey: stale-stub + naming-drift findings (mesell-knowledge-sync-data-session-1)
Read-only pipeline survey. Surprising/non-obvious findings only:

1. **`backend/app/data/category_attributes.json` and `meesho_categories.json` are STALE HAND-STUBS, not pipeline output.** Both dated May 27 (pre-parse). `category_attributes.json` = 16 hardcoded categories (Kurtis/Sarees/etc.) with `required/optional/default_return_rate` — a quality-engine return-rate stub, NOT the 3,772-leaf attribute schema. `meesho_categories.json` = a hand-typed 6-super-cat nav tree with made-up sub-cats (e.g. "Beauty & Personal Care") that do NOT match the real `meesho_category_tree.json` super-category names. The REAL derived corpus lives in `backend/app/data/meesho_category_tree.json` (1.7MB, 3,772 leaves, API-sourced 2026-06-03) + the DB seed pipeline. The two stubs are legacy/quality-engine fixtures — must NOT be confused with the canonical category data. Watch for downstream code reading the wrong file.

2. **My spec names `category_attributes.json` as a derived file I schema-version. It is NOT pipeline-derived.** The actual derived artifacts are `meesho_category_tree.json` (tree) + DB tables seeded from `data/parsed/batch_*.json`. The schema-versioned surface is the batch JSON `parser_version` (currently 0.2) and the alias `_meta.version` (currently 1) — NOT a version stamp inside category_attributes.json.

3. **No scraper tooling exists yet.** No `scripts/scrape*`, no `data/snapshots/`, no Playwright scraper. `meesell-scraper-maintainer` has produced zero artifacts. The 2026-06-03 tree came from a direct Meesho API call (`api:bulkCatalogUpload/fetchCategoryTreeOld`), recorded in the tree's `source` field — not from the scraper. Quarterly refresh has no executable scraper pathway today.

4. **Count reconciliation (all within locked tolerance, documented in seed_all.py):** templates SSoT 3,557 → actual 3,566 (+9, from schema groups differing only by enum_source/help_text); field_enum_values SSoT 49,295 → actual 49,259 (−36, from alias-collision dedup of duplicate (category_id, canonical) pairs). field_aliases exact 67. categories exact 3,772. `leaf_id_to_schema_hash.json` confirms 3,772 leaves → 3,566 distinct hashes on disk.

5. **Naming drift: SSoT/analysis say "16+ alias families"; actual `canonical_field_aliases.json` has 23 families and seeds 67 field_aliases rows.** `_meta.version=1`. onboarding_extension_map is keyed by numeric super_id strings (e.g. "26", "19_36_37_14_88_34") not super-category names.

6. **30 super-categories in the real tree** (tree meta: super_category_count=30, category_count=234, sub_category_count=1046), vs the 6 invented in the stub `meesho_categories.json`. 12 parse batches grouped these 30 supers thematically.

## MEMORY.md
- [Knowledge-sync survey 2026-06-10](#2026-06-10--knowledge-sync-survey-stale-stub--naming-drift-findings-mesell-knowledge-sync-data-session-1) — category_attributes.json + meesho_categories.json are stale hand-stubs; real corpus is meesho_category_tree.json + DB seed; no scraper exists yet; count tolerances locked in seed_all.py
- [Session mesell-repo-management-session-1](#session-mesell-repo-management-session-1--step-5--data-engineer-spec-evolved-into-data-lead-spec-feature_board_datamd-initialised) — Data Lead spec rewrite + feature_board_data.md initialisation per MASTER_PLAN §6 + §7
- [Founder's batch workflow preference](#2026-06-04--founders-batch-workflow-preference-locked) — full-corpus, batch-by-batch, discussion-gated
- [Workspace hook conflict fallback](#2026-06-04--workspace-hook-conflict--one-time-fallback-pattern) — when meesell-* dispatch is blocked, use nexus python-developer-agent with memory routed to meesell-*/MEMORY.md
- [SSoT integration is manual](#2026-06-04--ssot-integration-is-manual-never-automated) — coordinator + founder write it, never the specialist
- [All deliverables complete](#2026-06-04--all-data-layer-deliverables-complete) — SSoT locked 2026-06-04; downstream sessions unblocked
- [Gap analysis 2026-06-05](#2026-06-05--mvp_architecture-gap-analysis-dispatched--delivered) — 18 gaps catalogued, 4 Tier-1 BLOCKER-V1, R1–R5 reconciliation plan; root cause of doc drift = draft sections inserted without renumbering
