# Memory — meesell-database-builder

## Agent Identity
Database specialist for MeeSell. Owns SQLAlchemy 2.0 async ORM models + Alembic migrations + seed scripts for the 13 V1 tables (supersedes old "7 V1 tables" reference — use MVP_ARCHITECTURE §2 + §10 as the contract).

---

## Index
> Bodies live in `mem/`. ⭐ = contains reusable pattern / gotcha / ground-truth.

- ⭐ [§19 multi-tenant regression CONSTRUCTED (2026-06-08, Wave 7 step 2)](mem/mem_01_19-multi-tenant-regression-constructed-2026-06-08-wave-7-ste.md)
- ⭐ [§5 shared CONSTRUCTED (2026-06-06)](mem/mem_02_5-shared-constructed-2026-06-06.md)
- ⭐ [Phase 1 — ORM Models COMPLETE (2026-06-05)](mem/mem_03_phase-1-orm-models-complete-2026-06-05.md)
- [Phase 2 — Alembic Baseline Migration COMPLETE (2026-06-05)](mem/mem_04_phase-2-alembic-baseline-migration-complete-2026-06-05.md)
- [Phase 3 — Seed Scripts COMPLETE (2026-06-05)](mem/mem_05_phase-3-seed-scripts-complete-2026-06-05.md)
- ⭐ [Phase 4 — Smoke Tests COMPLETE (2026-06-05)](mem/mem_06_phase-4-smoke-tests-complete-2026-06-05.md)
- ⭐ [Phase 5 — Code-side Gap Fixes (G6, G7, G10-index) COMPLETE (2026-06-05)](mem/mem_07_phase-5-code-side-gap-fixes-g6-g7-g10-index-complete-2026-06.md)
- ⭐ [Session 2 Gap Pass — G4+G1 COMPLETE (2026-06-05)](mem/mem_08_session-2-gap-pass-g4-g1-complete-2026-06-05.md)
- [Session 3 — GIN trgm ORM sync (2026-06-05)](mem/mem_09_session-3-gin-trgm-orm-sync-2026-06-05.md)
- [Phase 7 — DATABASE_ARCHITECTURE.md authored (2026-06-05)](mem/mem_10_phase-7-database-architecture-md-authored-2026-06-05.md)
- ⭐ [MS Sub-Plan A Phase A — svc-export Alembic schema-split COMPLETE (2026-06-12)](mem/mem_11_ms-sub-plan-a-phase-a-svc-export-alembic-schema-split-comple.md)
- ⭐ [Category Seeding Wave 1 — LOCAL-ONLY seed COMPLETE (2026-06-16)](mem/mem_12_category-seeding-wave-1-local-only-seed-complete-2026-06-16.md)
- ⭐ [MS Sub-Plan B Phase A — svc-dashboard DB attestation B4 (2026-06-13) [meesell-database-builder AUTHORITATIVE]](mem/mem_13_ms-sub-plan-b-phase-a-svc-dashboard-db-attestation-b4-2026-0.md)
- [Category Seeding Wave 3 — Wizard-chain verification COMPLETE (2026-06-16)](mem/mem_14_category-seeding-wave-3-wizard-chain-verification-complete-2.md)
- ⭐ [Razorpay PR #323 — Alembic Multi-Head Fix COMPLETE (2026-06-20)](mem/mem_15_razorpay-pr-323-alembic-multi-head-fix-complete-2026-06-20.md)
