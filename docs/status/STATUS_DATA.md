# STATUS — DATA / SCRAPER

**Owner:** DATA sub-session
**Last update:** 2026-06-04

**Status:** Session not yet started — initialize by opening a new Claude session and pasting the DATA / SCRAPER prompt from `docs/SESSION_PROMPTS.md`.

## Current Phase
Phase 1, 2, 3 — **ALL FOUNDATION WORK COMPLETE.**

- Phase 1 (Full-corpus parse): ✅ 3,772/3,772 leaves, 0 failures
- Phase 2 (Use case discovery): ✅ covered by FULL_CORPUS_ANALYSIS.md (12 sections)
- Phase 3 (MVP Architecture): ✅ docs/MVP_ARCHITECTURE.md drafted

**Phase 4-5 BLOCKED** on founder approval per original session brief — but all data deliverables are complete and downstream sessions (BACKEND/FRONTEND/AI) are fully unblocked via MVP_ARCHITECTURE.md + MEESHO_CATEGORY_INTELLIGENCE.md.

**Section 7 open questions in MVP_ARCHITECTURE.md — all 6 LOCKED by founder 2026-06-04 evening:**
1. Books ISBN → optional (follow Meesho)
2. Meesho typos → auto-correct internally, restore on XLSX export
3. Long-tail super-categories → include all 3,772 in V1
4. Group ID → show inline as Optional
5. Warranty → per-product wizard step (match Meesho)
6. Eye-Serum collapsed compliance → store both, render per category

**Post-philosophy revisions (locked):**
- Decision #12 revised: Group ID → show behind "Advanced fields" toggle (Pattern 5 from CORE_PHILOSOPHY.md)
- Decision #14 revised: Eye-Serum → collect 9 standard fields universally, Export Adapter concatenates only at XLSX export (philosophy F4 — never store data we don't need)

**Architecture extended with 5 new sections (2026-06-04 evening):**
- §6 Caching Strategy (Valkey DB 3, version-tagged keys, ~57MB footprint)
- §7 Search & Indexing (pg_trgm GIN, 3 indexes, P95 ≤200ms)
- §8 AI Model Operations (₹0.05/call, 3-layer enum guardrail, ₹500/day cap)
- §9 Multi-tenancy and Data Isolation (app-level user_id scoping, JWT, 4 rate limits)
- §10 Audit Log and Autosave Events (5-min PATCH coalescing, abuse detection, 90d retention)

**Housekeeping complete (2026-06-04 evening):**
- §11 Hand-off Contracts extended with 5 new sub-sections (11.4-11.8) for the new sections
- §12 Founder-Locked Decisions updated with the 2 post-philosophy revisions
- §13 Risks updated with 3 new risks (RLS deferred SPOF, Valkey SPOF, AI cost overrun)
- §14 Phased Rollout extended with 6 new V1.5 items (RLS migration, admin panel, team accounts, A/B testing for AI, Valkey HA, dropdown jargon translation)
- §15 Sign-off updated to reflect 14 of 14 founder decisions

**Final MVP_ARCHITECTURE.md size: 135 KB across 15 numbered sections.**

Batches 5-12 executed in **parallel** (single bash command with `&` and `wait`, total wall time 167 seconds). Cross-batch analysis performed sequentially as founder directed. All per-batch summaries written. Comprehensive synthesis at `data/parsed/FULL_CORPUS_ANALYSIS.md`.

**Top 10 corpus-wide findings:**
1. **Strict TRUE universals: 15 fields** (down from claimed 26 — B1-B4 over-estimated because Eye-Serum's collapsed compliance representation only surfaced in B10)
2. **Practical universals (≥99% coverage): 28 fields** — the V1 core form
3. **0 Recommended-Field markers** in 3,772 leaves. Two-tier form permanently locked.
4. **Image rule uniform** (4 slots, slot 1 compulsory) across ALL 3,772 leaves
5. **1,831 unique field names** — data-driven primitive library is mandatory (10 primitives cover everything)
6. **291 Brand-pattern fields** (same name, different enum source per category)
7. **Onboarding extensions confirmed for 6 super-categories**: Grocery+FSSAI (COMPULSORY!), Kids+BIS, Electronics+R/IS/CM-L, Beauty+License/Registration, Books+ISBN, Appliances+License
8. **Compulsory median range: 19-33** across super-categories. Wizard step count MUST be data-driven.
9. **3,557 distinct templates serve 3,772 leaves** (5.7% dedup) — schema-by-template strategy holds
10. **Canonical field-name normalisation layer is mandatory** — 16+ alias families discovered (Battery has 6 variants, Compatible has 4, Color/Colour, Warranty has 5, etc.)

**Deliverables — ALL COMPLETE:**
- `docs/MEESHO_CATEGORY_INTELLIGENCE.md` — ✅ SSoT co-authored by coordinator + founder 2026-06-04 (424 lines, 9 sections, locked)
- `data/parsed/canonical_field_aliases.json` — ✅ COMPLETE (16+ alias families)
- `docs/MVP_ARCHITECTURE.md` — ✅ COMPLETE (2,796 lines, 15 sections, 14/14 founder decisions)

Coordinator-implements fallback was used for all parsing (workspace agent registration still pending).

## Done
- Refreshed identity: `meesell-data-engineer` (Opus, coordinator role, 2 specialists: xlsx-parser + scraper-maintainer)
- Read formal spec, MEMORY.md (empty), MEESELL_AGENT_REGISTRY.md, CLAUDE.md (new agent ecosystem section), V1_FEATURE_SPEC.md, VALIDATED_PAIN_POINTS.md, PLAYWRIGHT_MCP_REFERENCE.md
- Confirmed 18-agent ecosystem live in `.claude/agents/meesell-*.md`
- Confirmed 3,772 XLSX templates on disk (exact match to leaf count in category tree)
- Confirmed no prior XLSX sample parsing done (MEMORY.md is empty, no parse scripts in `scripts/`)
- `docs/MVP_ARCHITECTURE.md` does NOT exist — will be created in Phase 3

## In Progress
- (none — awaiting founder GO before Phase 1)

## Blockers
- BACKEND, FRONTEND, AI sessions cannot proceed until docs/MVP_ARCHITECTURE.md is delivered (this session is the foundation gate)

## Next
- Phase 1 — Real Data Analysis: sample 1 XLSX per super-category (30 total), extract structure + variance metrics
- Phase 2 — Use Case Discovery: surface category-level findings (e.g. Sarees-specific decisions, brand dropdown range)
- Phase 3 — MVP Architecture Proposal: author docs/MVP_ARCHITECTURE.md (data model, form renderer, AI strategy, indexing, caching)
- STOP after Phase 3. Report to master. Phase 4-5 only after approval.

## Hand-offs
- Pending (will queue post-Phase 3): MVP_ARCHITECTURE.md → meesell-backend-coordinator (data model), meesell-frontend-coordinator (form renderer), meesell-ai-coordinator (prompt budget given schema variance)

## Updates Log

=== UPDATE: 2026-06-04 ssot-complete ===
Phase: SSoT co-authorship — COMPLETE
Done:
  - Wrote docs/MEESHO_CATEGORY_INTELLIGENCE.md (424 lines, 9 sections)
    §1 Scale & scope (12 metrics governing all architecture decisions)
    §2 28 practical universals (7 always-compulsory / 8 always-optional / 13 near-universal)
    §3 Two-section data model — onboarding bucket (10 base + 6 conditional extensions) + catalog wizard bucket
    §4 10 input primitives (classification rules, UI component mapping)
    §5 291 Brand-pattern fields (backend storage requirement, API endpoint pattern)
    §6 Canonical field-name alias map (16 families, typo handling, XLSX round-trip rule)
    §7 Onboarding compliance extensions (7 super-categories, evidence counts, wizard behaviour)
    §8 Corpus-wide invariants (hardcode-safe constants)
    §9 Locked decisions index (14 decisions, one-liner each, cross-ref to MVP_ARCHITECTURE.md)
  - STATUS_DATA.md updated to reflect all deliverables complete
All data-layer deliverables are now complete. BACKEND/FRONTEND/AI sessions are fully unblocked.
Blockers: none
Next: founder unblocks downstream sessions (meesell-backend-coordinator, meesell-frontend-coordinator, meesell-ai-coordinator)
Hand-offs ready:
  - DATA → BACKEND: docs/MEESHO_CATEGORY_INTELLIGENCE.md + docs/MVP_ARCHITECTURE.md §2+§3 + canonical_field_aliases.json + all batch JSONs
  - DATA → FRONTEND: MEESHO_CATEGORY_INTELLIGENCE.md §3+§4 + MVP_ARCHITECTURE.md §4 (10 primitives, wizard renderer, onboarding wizard)
  - DATA → AI: MEESHO_CATEGORY_INTELLIGENCE.md §5+§9 + MVP_ARCHITECTURE.md §5 (Smart Picker top-5, enum-constrained autofill)
=========


=== UPDATE: 2026-06-04 00:00 ===
File initialised by master session. Awaiting first DATA sub-session.
=========

=== UPDATE: 2026-06-04 session-start ===
DATA sub-session opened. Orientation complete.
- meesho_category_tree.json: 3,772 leaves, sourced from Meesho API. Clean.
- data/meesho_templates/: 3,772 XLSX files present (exact match to leaf count).
- category_attributes.json: STUB — 16 entries (15 named + _default), hand-written, not derived from template parsing. Critical gap.
- PLAYWRIGHT_MCP_REFERENCE.md: 6-phase scraping workflow documented, battle-tested patterns in place.
- No active blockers. Awaiting founder task.
=========

=== UPDATE: 2026-06-04 refresh-to-foundation-role ===
Phase: orientation
Role: formally promoted to `meesell-data-engineer` (coordinator). 18-agent ecosystem now active.
Mission: deliver docs/MVP_ARCHITECTURE.md grounded in real XLSX data. BACKEND/FRONTEND/AI sessions are blocked on this output.
Done: read spec + empty memory + registry + CLAUDE.md ecosystem rules + V1_FEATURE_SPEC + VALIDATED_PAIN_POINTS + Playwright reference. Verified prior state: no parse scripts, no MVP_ARCHITECTURE.md, no sample analysis done — this is greenfield.
Coverage: 0 / 3,772 templates parsed.
Schema version: category_attributes.json v0 (stub, 16 entries).
In progress: none — awaiting founder GO before Phase 1.
Blockers: none on my side; downstream sessions blocked on me.
Next: Phase 1 sample of 30 XLSX (1 per super-category) on GO.
Hand-offs: queued — MVP_ARCHITECTURE.md → backend-coordinator (data model), frontend-coordinator (renderer), ai-coordinator (prompt budget).
=========

=== UPDATE: 2026-06-04 mvp-architecture-drafted ===
Phase: Phase 3 — MVP Architecture COMPLETE
Done:
  - Wrote docs/MVP_ARCHITECTURE.md (10 sections, ~17 KB)
    Section 0: 10 corpus-grounded premises
    Section 1: System architecture diagram
    Section 2: PostgreSQL DDL (10 tables: users, seller_profile, templates, categories, field_enum_values, field_aliases, catalogs, products, product_images, pricing_calcs, exports)
    Section 3: 24 API endpoints (auth, seller-profile suite, categories, products, exports)
    Section 4: Frontend architecture — 11 primitive components, data-driven wizard, onboarding wizard
    Section 5: AI pipeline — Smart Picker (top-5), Auto-fill (enum-guardrailed), Image pre-check
    Section 6: Hand-off contracts — DATA→BACKEND, DATA→FRONTEND, DATA→AI (each with inputs delivered, jobs, acceptance criteria)
    Section 7: 6 open questions for founder
    Section 8: Risk register (9 risks + mitigations)
    Section 9: V1/V1.5/V2 phased rollout
    Section 10: Sign-off
  - Wrote data/parsed/canonical_field_aliases.json with 20+ alias families
    (Color/Colour, Battery family 6 variants, Compatible family 4 variants, Manufacturer/Packer/Importer 9-field vs combined, Brand spelling variants, FSSAI, BIS/ISI, ISBN, License family, Warranty family, Camera typos preserved verbatim, etc.)
    + onboarding_extension_map keyed by super_id
Coverage / outputs:
  - All deliverables for BACKEND/FRONTEND/AI hand-off are ready
  - SSoT (docs/MEESHO_CATEGORY_INTELLIGENCE.md) deferred to founder co-authorship at laptop (per founder rule "we discuss and integrate together")
Blockers:
  - Founder review of docs/MVP_ARCHITECTURE.md
  - Founder answers to Section 7's 6 open questions (Books ISBN strictness, Eye-Serum collapsed compliance handling, Meesho typos preserve-or-correct, Group ID handling, long-tail super-categories, Warranty as onboarding-or-per-product)
  - Phase 4 (V1 feature validation) and Phase 5 (Micro-PoC) blocked on founder approval per session brief
Next:
  - Founder reviews docs/MVP_ARCHITECTURE.md (especially Section 7 open questions)
  - Founder approves to unblock Phases 4-5 OR directly unblock BACKEND/FRONTEND/AI sessions
  - Once SSoT is co-authored, the MVP architecture can be tied to specific SSoT lines
Hand-offs ready (queued):
  - DATA → BACKEND: MVP_ARCHITECTURE.md §2, §3, canonical_field_aliases.json, parsed JSONs
  - DATA → FRONTEND: MVP_ARCHITECTURE.md §4 (11 primitives, wizard renderer, onboarding wizard)
  - DATA → AI: MVP_ARCHITECTURE.md §5 (Smart Picker top-5, enum-constrained autofill, image pre-check)
=========

=== UPDATE: 2026-06-04 full-corpus-complete ===
Phase: Phase 1 — FULL CORPUS PARSE COMPLETE (Batches 5-12, parallel execution)
Done:
  - Parser v0.2 — tightened image_url detection (fixed Webcams false-positive), expanded number-name keywords (MRP, Inventory, Voltage, etc.)
  - All 12 batches (B1-B4 re-parsed, B5-B12 new) launched in PARALLEL via single bash command
  - Wall time: 167 seconds (vs estimated 10x sequential)
  - 3,772/3,772 leaves parsed cleanly. 0 failures across entire Meesho corpus.
  - Per-batch summaries: batch_NN_summary.md for N=1..12
  - Comprehensive synthesis: data/parsed/FULL_CORPUS_ANALYSIS.md (12 sections)
  - Memory updated: meesell-xlsx-parser/MEMORY.md with full corpus findings + deliverables index
Coverage: 3,772 / 3,772 (100%)
Top findings driving MVP architecture:
  - 15 STRICT true universals + 28 PRACTICAL universals (≥99% coverage)
  - 0 Recommended fields anywhere → V1 form is two-tier
  - Image rule 4/1 uniform everywhere → image UI design solved
  - 1,831 unique field names → 10 input primitives cover them all
  - 291 Brand-pattern fields → API-backed search picker for large enums (>500), other primitives for smaller
  - 6 onboarding compliance extensions confirmed (Grocery FSSAI compulsory!, Kids/Electronics BIS, Beauty License, Books ISBN, Appliances License)
  - Compulsory median 19-33 by super-category → wizard step count data-driven
  - 3,557 distinct templates / 3,772 leaves (5.7% dedup) → schema-by-template strategy
Key discovery (B10):
  - Eye-Serum leaf (12378) uses "Manufacturer Details" single-field compliance instead of standard 9-field block. Forces 26→15 strict universal claim AND validates the canonical-name normalisation requirement.
Blockers:
  - Workspace agent registration STILL unfixed (meesell-* not in subagent discovery). Coordinator-implements fallback used for all 12 batches.
  - Founder review of FULL_CORPUS_ANALYSIS.md required to drive SSoT writing + MVP architecture
Next:
  - Founder reads FULL_CORPUS_ANALYSIS.md highlights (mobile-readable summary in chat)
  - When at laptop: co-author docs/MEESHO_CATEGORY_INTELLIGENCE.md (SSoT) from accepted findings
  - Then: docs/MVP_ARCHITECTURE.md (Phase 3 deliverable) driven by corpus truths
  - Unblock BACKEND/FRONTEND/AI sessions
Hand-offs queued for after SSoT+architecture lock:
  - meesell-backend-coordinator: data model (templates, categories, field_enum_values, seller_profile.compliance_extensions, field_aliases)
  - meesell-frontend-coordinator: 10-primitive input library, data-driven wizard, onboarding with conditional extension steps
  - meesell-ai-coordinator: per-category prompts with compressed schema, enum-constrained auto-fill
=========

=== UPDATE: 2026-06-04 batch-4-complete ===
Phase: Phase 1 — Batch 4 (Consumer Electronics) COMPLETE
Done:
  - Ran parser on super_id=16 → 248/248 leaves, 0 failures, 0 anomalies
  - Output: data/parsed/batch_04_consumer_electronics.json
  - Draft findings (15 sections): data/parsed/batch_04_summary.md
  - meesell-xlsx-parser/MEMORY.md updated with B4 results, parser v0.2 fix queue, canonical field-name proposal
Coverage: 817 / 3,772 cumulative (21.7%)
Top findings from B4 + cross-batch:
  - 26 TRUE universals STILL HELD (4 batches, zero attrition — extremely stable foundation)
  - 151 NEW fields introduced (largest expansion yet)
  - Warranty Type appears in 149/248 all-compulsory → conditional Electronics wizard step
  - Compatible Models is NEW LARGEST DROPDOWN at 4,481 values (beats Brand's 3,998) — same API-backed picker primitive
  - Indian regulatory IDs (R Number 106 leaves, IS Number 112, CM/L 26, BIS 20) — all optional, all seller-specific → strong evidence for decision #9 (conditional onboarding)
  - Tech-spec attributes: Voltage, Wattage, Frequency, Capacity, USB Ports, Bluetooth — need NEW primitive: number_with_unit (V/W/Hz/mAh/cm/g)
  - Median compulsory STILL 24 (matches B3, lower than Fashion's 27-28) — pattern: Fashion=long, others=medium
  - Recommended fields = 0 (817/817 leaves)
  - Synonym drift: 6 variants of Battery in B4 (Battery / Battery Required / Battery Available / Batteries Required / Batteries Included / Battery Type). Canonical normalisation layer can't wait.
Parser bug surfaced:
  - "Still Image Sensor Resolution" (Webcams) mis-classified as image_url. v0.2 fix queued.
Blockers:
  - Workspace agent registration unchanged
  - Founder review of batch_04_summary.md required
Next:
  - Founder reads B4 highlights, ideally locks decision #9 (conditional onboarding) now
  - Batch 5 = Home & Kitchen part A (~280 leaves), super_id=30
Hand-offs: queued until all 12 batches + SSoT lock
=========

=== UPDATE: 2026-06-04 batch-3-complete ===
Phase: Phase 1 — Batch 3 (Kids & Toys) COMPLETE
Done:
  - Ran `scripts/parse_meesho_xlsx.py --super-ids 13` → 284/284 leaves parsed, 0 failures, 0 anomalies
  - Output: `data/parsed/batch_03_kids_toys.json`
  - Draft findings (15 sections, cross-batch enriched): `data/parsed/batch_03_summary.md`
  - Updated `meesell-xlsx-parser/MEMORY.md` with Batch 3 results + new patterns
Coverage: 569 / 3,772 cumulative (15.1%)
Top findings from Batch 3 + cross-batch with B1+B2:
  - 26 TRUE universals UNCHANGED — zero attrition through 3 batches
  - 149 NEW fields introduced (biggest expansion yet vs B2's 49)
  - Compulsory median DROPPED to 24 (vs 27-28 in Fashion) — wizard cannot have fixed step count
  - Safety-critical fields surface: Product Dimensions, Recommended Age, Kids Weight, BIS/ISI Certification, Battery Required, Assembling Required
  - Brand-pattern field set grew 82 → 106 fields
  - Image rules uniform across all 569 leaves (still 100% pattern)
  - Recommended fields = 0 across 569 leaves (binary marker scheme strongly confirmed)
  - Template dedup in Kids = 13% (vs 1-6% in Fashion) — schema-by-template strategy saves more in Kids
  - DATA-QUALITY ISSUES at source: spelling drift (Colour/Color), synonym fields (Assembly/Assembling), concept fragmentation (Battery/Battery Required/Battery Available) — need canonical_field_name normalisation layer
  - NEW PATTERN: Onboarding bucket grows per super-category (Kids+BIS/ISI, predicted Grocery+FSSAI, Books+ISBN, Electronics+IEC) — seller profile needs compliance_extensions: jsonb keyed by super-category
Blockers:
  - Same workspace agent registration issue
  - Founder review of batch_03_summary.md required before integration discussion
Next:
  - Founder reads B3 highlights, decides on conditional-onboarding pattern
  - When at laptop: co-author SSoT entry covering B1+B2+B3
  - Authorize Batch 4 (Consumer Electronics, super_id=16, 248 leaves)
Hand-offs: none until all 12 batches + SSoT lock
=========

=== UPDATE: 2026-06-04 batch-2-complete ===
Phase: Phase 1 — Batch 2 (Men Fashion) COMPLETE
Done:
  - Ran `scripts/parse_meesho_xlsx.py --super-ids 10` → 106/106 leaves, 0 failures, 0 anomalies
  - Output: `data/parsed/batch_02_men_fashion.json`
  - Draft findings (13 sections, cross-batch enriched): `data/parsed/batch_02_summary.md`
  - Updated `meesell-xlsx-parser/MEMORY.md` with Batch 2 results and pattern validation
Coverage: 285 / 3,772 cumulative (7.6%)
Top findings from Batch 2 + cross-batch with Batch 1:
  - 26 TRUE universals locked (intersection of B1 ∩ B2 universals); none of B1's universals fell out
  - 0 Recommended fields across 285 leaves now — Meesho's marker scheme is binary, strong confidence
  - 82 fields show "Brand pattern" (same field name, enum size varies 50-3998 across categories) — input primitive library must auto-classify by enum_count
  - 49 NEW menswear fields (Chest Size, Waterproof, Number of Pockets, Toe Shape, etc.)
  - Image rules uniform across all 285 leaves (4 slots, 1 compulsory)
  - 105/106 distinct templates in B2 (~1% dedup); 169/179 in B1 (~6% dedup) — schema-by-template strategy holds
Critical discovery:
  - `meesell-xlsx-parser` is NOT REGISTERED as a dispatchable subagent type — Agent tool reports "Agent type not found"
  - Founder's 7 PM hook-fix needs to do agent REGISTRATION in addition to settings tweak
Blockers:
  - Same as Batch 1: workspace agent infrastructure incomplete; coordinator-implements fallback continues
  - Founder review of batch_02_summary.md required before integration discussion
Next:
  - Founder reviews batch_02_summary.md (mobile-readable highlights surfaced in chat)
  - When founder at laptop: co-author first integrated SSoT entry covering B1 + B2 in `docs/MEESHO_CATEGORY_INTELLIGENCE.md`
  - Authorize Batch 3 (Kids & Toys, super_id=13, 284 leaves)
Hand-offs: none until all 12 batches + SSoT lock
=========

=== UPDATE: 2026-06-04 batch-1-complete ===
Phase: Phase 1 — Batch 1 (Women Fashion + Women) COMPLETE
Done:
  - Wrote `scripts/parse_meesho_xlsx.py` v0.1 (openpyxl-based, ~250 lines)
  - Validated parser on 3 deliberately diverse samples: Sarees (10003), Mobile Cases & Covers (10382), Chaat Masala (14366) — all 3/3 parsed cleanly
  - Ran parser on super_id=11 + super_id=29 → **179/179 leaves parsed, 0 failures, 0 anomalies**
  - Wrote raw output: `data/parsed/batch_01_women_fashion.json`
  - Wrote draft findings (12 sections): `data/parsed/batch_01_summary.md`
  - Updated `.claude/agent-memory/meesell-xlsx-parser/MEMORY.md` with: attribution note, full parser design, Batch 1 results, MVP findings, guidance for Batches 2-12
Coverage: 179 / 3,772 cumulative (4.7%); Batch 1: 100% clean
Schema version: parser v0.1; `backend/app/data/category_attributes.json` UNCHANGED (still v0 stub — promoted only after all 12 batches + MVP lock)
Execution path: TWO-LEVEL FALLBACK — workspace hook blocked meesell-xlsx-parser → nexus:level-3:python-developer-agent timed out mid-recon (28 tool calls, no output) → coordinator implemented directly. One-time exception, documented in coordinator + xlsx-parser memory.
Top 3 surprises from data:
  1. Zero "Recommended Field" markers in 179 leaves — Women Fashion uses binary Compulsory/Optional only
  2. Brand dropdown up to 3,998 values per category — native <select> infeasible
  3. 9-field universal compulsory compliance block (Manufacturer/Packer/Importer × Name/Address/Pincode) — strong P0 auto-fill case
Blockers:
  - Workspace agent-routing hook still blocks meesell-* dispatches. Evening reminder scheduled (7 PM IST) to fix before Batch 2.
  - Founder review of `data/parsed/batch_01_summary.md` REQUIRED before discussion → SSoT integration
Next:
  - Founder reads batch_01_summary.md, annotates accept/reject/edit per section
  - Coordinator + founder write `docs/MEESHO_CATEGORY_INTELLIGENCE.md` (Batch 1 section integrated manually)
  - After hook fix: dispatch real `meesell-xlsx-parser` for Batch 2 (super_id=10 Men Fashion, 106 leaves)
Hand-offs: none yet — all 12 batches + SSoT must complete before BACKEND/FRONTEND/AI sessions unblock
=========
