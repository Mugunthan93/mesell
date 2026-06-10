# Feature Plan Canonical Pattern — v2

**Status:** LOCKED 2026-06-10 (replaces the implicit v1 pattern from PLANNING_DISPATCH.md Step 7)
**Owner:** Master Director session — amendments require founder approval
**Applies to:** Every `docs/plans/features/{feature-slug}/FEATURE_PLAN.md` in the V1 scope (9 features)

---

## Why this pattern exists

Between 2026-06-08 and 2026-06-10 the founder ran nine parallel planning sub-sessions — one per V1 feature — each isolated in its own `git worktree` per `docs/plans/features/_WORKTREE_PROTOCOL.md`. Each sub-session was dispatched with the same PLANNING_DISPATCH.md template, whose Step 7 listed the v1 pattern: **9 sections** (Decisions / Agent lineup / Code surfaces / Documentation deliverables / Dispatch templates / Review + iteration protocol / Acceptance gate / Risk register / Revision history). The intent was a uniform shape; the reality is that the v1 pattern was implicit (a bullet list inside Step 7 of a dispatch prompt, not a separate locked spec), and parallel sub-sessions diverged.

The Master Director session audited the 9 merged FEATURE_PLAN.md files on develop after the last planning PR merged. Findings:

1. **Every plan carries the first 5 canonical sections** (Decisions / Agent lineup / Code surfaces / Documentation deliverables / Dispatch templates) at h2 (`## `) depth in approximately the right order.
2. **All 9 plans are missing the last 4 sections universally** — Review + iteration protocol, Acceptance gate, Risk register, Revision history were named in Step 7 but never authored at h2 depth in any plan. Some plans tucked half-formed versions inside ad-hoc subsections; none made them first-class.
3. **Two sections appear in 5-6 of the 9 plans as ad-hoc additions** — `Branch setup` (which sub-branches to cut, what to base them on, in what order to merge) and `Memory protocol` (which agent memories to read at coding-session start, where to write cross-feature memos). Sub-sessions independently discovered these were necessary; the v1 pattern omitted them.
4. **Sub-section depth errors are common** in `## Dispatch templates`: roughly half the plans used `## meesell-{specialist}` (h2) for each specialist instead of `### meesell-{specialist}` (h3), which flattens the table of contents and makes specialist prompts read as if they were top-level sections of the FEATURE_PLAN.

This v2 pattern locks the structure: the 5 sections that worked stay; the 4 universal gaps are promoted to canonical; the 2 commonly-added ad-hoc sections become canonical. Net total: **11 canonical sections in a locked order**. A separate document — `docs/plans/features/_AMENDMENT_DISPATCH.md` — carries a paste-able prompt the founder uses to bring each of the 9 existing plans into conformance.

This pattern v2 governs every NEW FEATURE_PLAN.md authored after the lock date. It also governs amendments to the 9 V1 plans.

---

## The 11 canonical sections (locked order)

A FEATURE_PLAN.md MUST contain these 11 sections, in this exact order, with the exact heading text shown (no number prefixes, no emoji, no variants):

### 1. ## Decisions
**Required content:** Founder D-numbered decisions verbatim from the planning session's Step 1. Locked thresholds, contracts, and scope assumptions. Each D-number gets its own `### D{N} — {short title}` h3 subsection with rationale, date, and consequences. If a decision was answered "as proposed" the section captures that with a `**Answer:**` line. Decisions are append-only after lock — if a later amendment overturns D2, append `### D2 — superseded 2026-06-MM` with the new ruling, leave the original verbatim above.

**Order rule:** D-numbers monotonically increase. No renumbering on amendment.

### 2. ## Agent lineup
**Required content:** A table mapping each involved lead to its specialists and what each specialist codes. Columns: `Lead | Specialists dispatched | What each specialist builds`. Only include leads that have work; omit empty rows. The `Lead` column uses the canonical agent slug (`meesell-backend-coordinator`, `meesell-frontend-coordinator`, `meesell-ai-coordinator`, `meesell-legal-writer`, `meesell-data-engineer`, or `meesell-infra-builder` as standalone). The `Specialists` column uses the canonical agent slug plus a one-line description of the code surface that specialist owns.

**Subsections allowed:** `### Dispatch order (critical path)` is recommended — a fenced text block showing PHASE A/B/C/D dependencies so the coding-session founder knows which specialists can run in parallel and which must serialize.

### 3. ## Code surfaces
**Required content:** A file-level inventory of every NEW + MODIFY across all involved tracks, grouped by domain (backend / frontend / ai / data / infra). One row per file with: file path (project-relative), `NEW` or `MODIFY` tag, brief description, owning specialist slug. The inventory MUST be exhaustive — if a file is touched during coding, it appears here. A subsection per track is encouraged (`### Backend`, `### Frontend`, `### Infra`).

**Cross-reference rule:** every row's "owning specialist" MUST appear in §2 Agent lineup. If a code surface needs a specialist not in §2, fix §2 first.

### 4. ## Documentation deliverables
**Required content:** List every doc artifact that must exist alongside merged code: OpenAPI entries (which endpoint, which schema), prompt registry entries (which prompt name + version), schema version notes (V1_FEATURE_SPEC §F{N} stamp), deployment runbooks (under `docs/runbooks/`), `BACKEND_ARCHITECTURE.md` or `MVP_ARCHITECTURE.md` section amendments. These items are gate conditions in §9 Acceptance gate — coding-stage PRs cannot merge without them.

### 5. ## Branch setup
**Required content (PROMOTED FROM AD-HOC — 6 of 9 V1 plans had this):**

A table of branches to create, cut from where, with the purpose and which agent commits to each. Standard shape:

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/{slug}` | `develop` | Integration branch; only merge commits | Lead coordinators (merge approval only) |
| `feature/{slug}/backend` | `feature/{slug}` | All backend specialist work | Backend specialists |
| `feature/{slug}/frontend` | `feature/{slug}` | All frontend specialist work | Frontend specialists |
| `feature/{slug}/infra` | `feature/{slug}` | All infra work | meesell-infra-builder |
| `feature/{slug}/ai` | `feature/{slug}` | All AI work | AI specialists (only when AI is involved) |
| `feature/{slug}/data` | `feature/{slug}` | All data work | Data specialists (only when data is involved) |

**Required subsections:**
- `### Creation commands` — verbatim `git checkout && git push -u origin ...` block the founder runs after the planning PR merges
- `### PR flow (coding stage)` — ascii diagram of which group PR merges into which target; reviewer per PR per the MASTER_PLAN §6 reviewer rule (group → integration: lead reviews; integration → develop: founder reviews)
- `### PR templates` — table mapping each group PR to its `.github/PULL_REQUEST_TEMPLATE/{group}.md`
- `### Rebase strategy` — what happens when a sibling group PR lands first and the next group PR needs to rebase onto the moved integration tip

### 6. ## Memory protocol
**Required content (PROMOTED FROM AD-HOC — 5 of 9 V1 plans had this):**

Which agent memories will be touched during coding-session execution and the cross-agent read paths. Specifically:

- **Memories the coding-session leads MUST read at start:** list of `.claude/agent-memory/meesell-{role}/MEMORY.md` paths for every lead + specialist on this feature
- **Cross-feature memos:** if this feature consumes contracts from a prior feature (e.g., `assert_product_ownership` from catalog-form is consumed by image, pricing, export), name the per-feature memo file under the consuming agent's memory directory (e.g., `.claude/agent-memory/meesell-backend-coordinator/feature_{slug}.md`)
- **Naming convention for new memos created during this feature:** `feature_{slug}.md` (or `{slug}_feature.md` for the file-system-sorted variant — but ONE convention must be picked per feature, not both)
- **Session-close memory entries:** what each agent appends to its own MEMORY.md at coding-session close (typically: session header, decisions ratified, files touched count, blockers carried, next-step recommendation)

### 7. ## Dispatch templates
**Required content:** ONE subsection per specialist dispatched during the coding stage. **Each subsection uses `### h3`, NEVER `## h2`.** Each `### {specialist-slug}` subsection contains a fenced ```PROMPT block (or untagged code fence) with the full paste-able dispatch prompt the founder will copy into a sub-session for that specialist. Each prompt MUST include:

1. `PROJECT BOUNDARY:` declaration (project name, path, never-cross rule)
2. `SESSION:` header following MASTER_PLAN §4 convention (`mesell-{slug}-{group}-session-{N}`)
3. `## Mandatory reads (in this order)` — bullet list of files to read before starting
4. `## Your mission` — 1-3 paragraphs naming the precise contracts the specialist must implement
5. `## Acceptance criteria` — checkbox list (every condition that makes the specialist's PR mergeable)
6. `## Hard constraints` — what the specialist must NOT touch
7. `## Files you MAY touch` — explicit allowlist
8. `## Files you must NOT touch` — explicit denylist (defense in depth)
9. `## Final report format` — what the specialist returns to the lead before opening a PR

The h3 (`###`) for each specialist is critical: the contents of the prompt live inside the code fence and DO NOT participate in the markdown heading hierarchy.

### 8. ## Review + iteration protocol
**Required content (UNIVERSAL GAP — present in zero of 9 V1 plans):**

For EACH specialist named in §2 Agent lineup, define:

- **Pre-approval checklist** — what the owning lead inspects before approving the specialist's PR (e.g., for the backend lead: "Lua rotation uses `EVALSHA` with `EVAL` fallback on `NOSCRIPT`; HMAC lookup uses `secrets.compare_digest()`; access JWT TTL reads from `ACCESS_TOKEN_TTL_SECONDS` env var, not a hardcoded constant"). Be specific to this feature, not generic.
- **PR-template gate** — quote the path to `.github/PULL_REQUEST_TEMPLATE/{group}.md`. The PR description MUST follow the template.
- **Re-dispatch triggers** — specific failure modes that make the lead reject the PR and re-dispatch the specialist. Examples: "Lua script uses MULTI/EXEC instead of EVAL → re-dispatch with §4.B counter-proposal 1 quoted"; "AuthService stores token in `localStorage` → re-dispatch with FE-D5 quoted"; "Cookie missing `SameSite=Strict` → re-dispatch with cookie-attr table from §4.G".
- **Re-dispatch prompt shape** — a one-paragraph template: the original dispatch prompt + a preamble "Previous run failed on X; fix Y by reading Z (specific file + section)".
- **Iteration cap** — maximum re-dispatches before escalating to the founder. Recommended: **3**. The third re-dispatch automatically triggers a founder consult.

### 9. ## Acceptance gate
**Required content (UNIVERSAL GAP — present in zero of 9 V1 plans):**

A checkbox list capturing what makes this feature "done overall". When every checkbox is `[x]`, the integration branch `feature/{slug}` is ready to merge to `develop`. Mix of:

- `[ ]` Each specialist PR (`feature/{slug}/{group}` → `feature/{slug}`) merged
- `[ ]` Integration tests green on the integration branch (paste the test command — typically `cd backend && pytest tests/integration/test_{slug}.py` plus a frontend e2e variant)
- `[ ]` Documentation deliverables landed (cross-reference §4)
- `[ ]` V1_FEATURE_SPEC.md acceptance criteria met — quote the specific bullet IDs (e.g., "§F1.AC1 — Send OTP responds 200 within 2s; §F1.AC2 — Verify OTP issues access JWT + refresh cookie")
- `[ ]` CI gates 1-5 green on the integration branch (lint, typecheck, unit tests, integration tests, build)
- `[ ]` Founder approval on the `feature/{slug}` → `develop` PR

### 10. ## Risk register
**Required content (UNIVERSAL GAP — present in zero of 9 V1 plans):**

3-5 risks specific to this feature. Format:

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | <risk description> | Low / Medium / High | Low / Medium / High | <mitigation, with file or section reference> |

Feature-specific risk examples (pick from your feature, do not copy verbatim):

- **auth-otp:** MSG91 staging credit exhaustion; Lua `EVAL` incompatibility with older Valkey; HMAC pepper rotation breaking live sessions; cookie domain mismatch dev↔staging; FE refresh storm on network flap
- **smart-picker:** Gemini rate limit during burst; pg_trgm fallback latency under load; category tree cache staleness
- **catalog-form:** autosave race conditions; per-IP-only rate limit collisions; draft-recovery TTL drift
- **ai-autofill:** invalid-enum bypass via prompt injection; Gemini cost spike during runaway autofill; fallback-offered=true UX confusion
- **image-precheck:** rembg GPU drift between dev/staging; GCS quota exhaustion; watermark prompt regression
- **live-preview:** stale-while-revalidate desync; ETag busting on schema version bump
- **price-calculator:** HSN-GST mapping gaps for new categories; rounding-error compounding
- **tracking-dashboard:** N+1 query under load; pagination cursor drift on parallel writes
- **xlsx-export:** Meesho template schema drift; openpyxl column-letter overflow at category-id 26+

### 11. ## Revision history
**Required content (UNIVERSAL GAP — present in zero of 9 V1 plans):**

A table tracking versions of THIS FEATURE_PLAN.md. Format:

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | YYYY-MM-DD | mesell-{slug}-planning-session-{N} | Initial FEATURE_PLAN.md authored |
| v2 | YYYY-MM-DD | mesell-{slug}-amendment-session-{N} | Canonical pattern v2 conformance |

Future amendments append rows. The FEATURE_PLAN.md is the single source of truth for its feature; the revision history is the audit trail.

---

## Per-feature variance — what's allowed and what's not

**ALLOWED:**
- **Plan length variance.** A small feature like live-preview may land at ~1000 lines; a complex one like xlsx-export may land at ~1800 lines. There is no maximum.
- **Section depth variance.** A simple §3 Code surfaces table may be 20 rows; a complex one may be 80. A simple §10 Risk register lists 3 risks; a complex one lists 5.
- **Subsection depth (`###`, `####`) inside any canonical section.** Plans may add subsections as needed. The constraint is on the h2 (`## `) layer.
- **Per-feature subsections inside §2 Agent lineup** for `### Dispatch order (critical path)`, `### Specialist-by-specialist dependencies`, etc.
- **Sibling files** inside `docs/plans/features/{slug}/` for content that doesn't fit one of the 11 sections (see below).

**NOT ALLOWED:**
- Section ordering changes — the 11 sections appear in the locked 1-11 order.
- Section heading text changes — exact text including capitalization, no numeric prefixes (`## 1. Decisions` is invalid), no emoji.
- Missing canonical sections — every plan has all 11, even if the content is brief (e.g., a feature with zero AI workload still has §6 Memory protocol).
- Ad-hoc top-level (`##`) sections not in the 11 — see the relocation rule below.

If a plan needs to surface information that doesn't fit one of the 11, it goes in EITHER:

1. **A subsection (`###`) inside the most-relevant canonical section** — e.g., `### Sprint plan` as a subsection of `## Agent lineup` (sprint plan describes execution order, which is an agent-lineup concern).
2. **A sibling `.md` file inside `docs/plans/features/{slug}/`** — e.g., `SPRINT_PLAN.md`, `AUDIT_FINDINGS.md`, `OPS_NOTES.md`. The sibling file is REFERENCED from the relevant canonical section (so a reader scanning the FEATURE_PLAN.md sees the pointer) but lives outside the plan to keep the plan focused.

---

## Sub-section depth rule (Dispatch templates)

Inside `## Dispatch templates`, EACH specialist gets a `###` (h3) subsection — NEVER a `##` (h2). This was a common v1 error: at least half of the 9 plans used h2 for each specialist, which flattens the TOC and makes the dispatch templates read as siblings of the canonical sections.

The canonical heading hierarchy is:

```
## Dispatch templates
### meesell-{specialist-1}
### meesell-{specialist-2}
### meesell-{specialist-3}
...
```

Inside each `### {specialist}` block, the prompt content (`## Your mission`, `## Mandatory reads`, `## Acceptance criteria`, etc.) lives inside a fenced code block. The headings INSIDE the code fence DO NOT participate in the markdown heading hierarchy — they are part of the paste-able prompt text, not the FEATURE_PLAN.md's own structure.

---

## How to use this pattern

**For new plans (post-V1 features):** When a new feature planning session starts, the planning sub-session reads THIS file FIRST (before V1_FEATURE_SPEC.md, before BACKEND_ARCHITECTURE.md), then authors the FEATURE_PLAN.md in this exact shape. The planning dispatch prompt for any feature beyond V1 MUST reference this canonical pattern by path.

**For existing V1 plans:** The 9 V1 plans are non-conforming. Use `docs/plans/features/_AMENDMENT_DISPATCH.md` to bring each into compliance — one paste-able prompt per feature, run in the feature's existing planning worktree at `/tmp/mesell-wt/{slug}/`. The amendment dispatch is idempotent (running it twice is harmless).

**For audits:** A reviewer scanning a FEATURE_PLAN.md for canonical-pattern conformance runs:

````
awk '/^(```|~~~)/{f=!f; next} !f && /^## /' docs/plans/features/{slug}/FEATURE_PLAN.md
````

This is fence-aware: it toggles a flag on every code-fence line and only matches `## ` headings outside fenced blocks. A naive `grep -nE "^## "` produces false positives because it counts h2-looking lines inside fenced dispatch-prompt code blocks — content the pattern itself says does not participate in the section hierarchy.

The expected output is exactly 11 lines, in the exact order:

```
## Decisions
## Agent lineup
## Code surfaces
## Documentation deliverables
## Branch setup
## Memory protocol
## Dispatch templates
## Review + iteration protocol
## Acceptance gate
## Risk register
## Revision history
```

Anything else (count != 11, wrong heading text, wrong order) flags as non-conforming.

---

## Revision history of this canonical pattern

| Version | Date | Author | Change |
|---|---|---|---|
| 2.0 | 2026-06-10 | master Director session + meesell-backend-coordinator | Initial LOCKED version. 11 sections (v1's 5 explicit + 4 universal gaps + 2 promoted ad-hoc). Replaces the implicit v1 pattern in PLANNING_DISPATCH.md Step 7. |
| 2.1 | 2026-06-10 | master Director session + meesell-backend-coordinator | Audit command made fence-aware; founder-approved |
