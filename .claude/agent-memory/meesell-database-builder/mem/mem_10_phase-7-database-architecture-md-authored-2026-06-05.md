## Phase 7 — DATABASE_ARCHITECTURE.md authored (2026-06-05)

### Canonical reference doc
`docs/DATABASE_ARCHITECTURE.md` is the single source of truth for the as-built MeeSell
database. It supersedes `docs/MVP_ARCHITECTURE.md` §2 for column-level DDL. It is 1,669 LOC,
14 sections.

### Section ownership map
| Section | Content | Phase/Dispatch that established it |
|---|---|---|
| §0 | Purpose + cross-references | Phase 7 (this dispatch) |
| §1 | High-level overview | Phase 7 — compiled from Phases 1-6 |
| §2.1-2.13 | Table-by-table (as-built) | Phase 7 — sourced from ORM models |
| §3 | ER diagram + cascade chains | Phase 7 |
| §4.1-4.9 | JSONB column contracts | Phase 7 — previously undocumented |
| §5 | Index inventory (44 indexes) | Phase 7 — compiled from ORM + migrations |
| §6 | Migration chain history | Phase 7 — sourced from alembic/versions/ |
| §7 | Seed pipeline architecture | Phase 7 — sourced from scripts/ + MEMORY |
| §8 | Connection patterns | Phase 7 — sourced from database.py + env.py |
| §9 | Multi-tenancy model | Phase 7 |
| §10 | Audit log + autosave | Phase 7 — cross-ref to MVP_ARCHITECTURE §10 |
| §11 | Testing strategy | Phase 7 — sourced from conftest.py + test files |
| §12 | Operational invariants | Phase 7 — sourced from MEMORY + seed smoke checks |
| §13 | V1 trade-offs + deferrals | Phase 7 |
| §14 | Maintenance + handoff | Phase 7 |

### Key decisions documented in this file
1. `docs/DATABASE_ARCHITECTURE.md` supersedes `MVP_ARCHITECTURE.md §2` for column-level DDL.
   Data-engineer should update §2 using this doc as source (G1, G2, G4, G11 gap items).
2. JSONB column contracts (Section 4) were previously undocumented anywhere — this is the
   canonical location. Any code writing JSONB must reference these shapes.
3. Section 5 lists 44 indexes total. After any migration, verify count with:
   `SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';`
4. K3s cluster API server at 34.180.58.185:6443 was unreachable during Phase 7 (connection
   refused). Live DB verification via `kubectl exec` was blocked. Schema documentation was
   verified entirely against ORM source files (which are the ground truth).

### Maintenance reminder
Every future dispatch that touches a model, migration, or seed MUST also update
`docs/DATABASE_ARCHITECTURE.md`. The doc will drift if this is not enforced.
Specifically: add a row to the Section 5 index table, add a new §2.N subsection for new
tables, update the head revision in Section 1 and Section 6.

---
