# Amendment Dispatch — Bring a FEATURE_PLAN.md into Canonical Pattern Conformance

**Use:** the founder pastes the inner prompt block into ONE Claude sub-session per feature (running in that feature's dedicated worktree at `/tmp/mesell-wt/{slug}/`). The sub-session audits its own FEATURE_PLAN.md, drafts amendments, commits, opens PR.

**Frequency:** one paste per feature. **9 sub-sessions total.**

**Authoritative pattern:** `docs/plans/features/_CANONICAL_PATTERN.md` (v2, LOCKED 2026-06-10).

**Aggregation:** each sub-session writes its own `_status/{slug}.yaml` and opens its own amendment PR. The master Director session aggregates state into `feature_planning_master.md` after each sub-session reports completion.

---

## Before launching any sub-session

1. **Verify the worktree exists.** For each feature you want to amend:

   ```
   cd /Users/mugunthansrinivasan/Project/mesell
   ./scripts/launch-planning-session.sh {feature-slug}
   ```

   The launcher script is idempotent — if the worktree already exists for `{slug}`, it reports `WORKTREE READY` (re-attached) and exits cleanly. If `/tmp/mesell-wt/{slug}/` was wiped by a reboot, the script recreates it from the existing branch on origin.

2. **Open a new Claude Code window** (do NOT reuse an existing session that may have stale context). `cd /tmp/mesell-wt/{feature-slug}` so the sub-session starts inside its worktree.

3. **Paste the prompt block below.** Substitute `{feature-slug}` wherever it appears — the prompt itself uses the slug as a placeholder.

4. **Wait for the sub-session to report `PLAN_READY` → `IN_REVIEW`** in its status file. Confirm via:

   ```
   cat /Users/mugunthansrinivasan/Project/mesell/docs/plans/features/_status/{slug}.yaml
   ```

   When status = `IN_REVIEW` with `pr_number` populated, the sub-session is done. Move to the next feature.

5. **Run amendments in any order.** No dependency exists between features at amendment stage (each plan is self-contained — the amendment touches ONLY its own FEATURE_PLAN.md). Sequential or parallel both work.

---

## The 9 features

| # | Slug | Worktree path | Branch |
|---|---|---|---|
| 1 | `auth-otp` | `/tmp/mesell-wt/auth-otp` | `feature/auth-otp/planning` |
| 2 | `smart-picker` | `/tmp/mesell-wt/smart-picker` | `feature/smart-picker/planning` |
| 3 | `catalog-form` | `/tmp/mesell-wt/catalog-form` | `feature/catalog-form/planning` |
| 4 | `ai-autofill` | `/tmp/mesell-wt/ai-autofill` | `feature/ai-autofill/planning` |
| 5 | `image-precheck` | `/tmp/mesell-wt/image-precheck` | `feature/image-precheck/planning` |
| 6 | `live-preview` | `/tmp/mesell-wt/live-preview` | `feature/live-preview/planning` |
| 7 | `price-calculator` | `/tmp/mesell-wt/price-calculator` | `feature/price-calculator/planning` |
| 8 | `tracking-dashboard` | `/tmp/mesell-wt/tracking-dashboard` | `feature/tracking-dashboard/planning` |
| 9 | `xlsx-export` | `/tmp/mesell-wt/xlsx-export` | `feature/xlsx-export/planning` |

---

## PASTE THIS PROMPT INTO EACH SUB-SESSION

Substitute `{feature-slug}` with the actual slug (e.g., `auth-otp`) wherever the placeholder appears. Everything between the outer fence markers is the paste-able block.

```
PROJECT BOUNDARY: You are working inside the git worktree for ONE feature at /tmp/mesell-wt/{feature-slug}/. The {feature-slug} placeholder is the directory you cd'd into. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/.
SESSION: mesell-{feature-slug}-amendment-session-1

## Step 0a — Worktree preflight (MANDATORY)

Verify you are in the right worktree before doing anything else:

  pwd                                       # must print /private/tmp/mesell-wt/{slug} or /tmp/mesell-wt/{slug}
  git worktree list | grep {slug}           # must show this worktree
  git branch --show-current                 # must print feature/{slug}/planning

If pwd is wrong, STOP. The founder must run scripts/launch-planning-session.sh {slug} from the main project tree first, then re-launch you in the correct worktree.

## Step 0b — Identify your feature

From your worktree path, extract your feature slug:

  FEATURE_SLUG=$(basename "$(pwd)")
  echo "Working on feature: $FEATURE_SLUG"

Substitute $FEATURE_SLUG everywhere below (including in commit messages, PR titles, and status file paths).

## Mandatory reads (in this order)

1. docs/plans/features/_CANONICAL_PATTERN.md — THE locked pattern v2. Read fully. This defines the 11-section shape your FEATURE_PLAN.md must conform to. EVERY rule in your amendment work traces back to this file.
2. docs/plans/features/{your-feature-slug}/FEATURE_PLAN.md — your current plan. Read fully. Note its current section structure, section count, heading text, and any ad-hoc sections.
3. docs/plans/features/_status/README.md — YAML status-file format. You will write to {your-feature-slug}.yaml twice during this session (start + close).
4. docs/plans/features/_WORKTREE_PROTOCOL.md — confirms worktree isolation rules. Re-read §7 (Gotchas + safeguards) — same-file race conditions on agent memory are real.
5. docs/plans/repo_management/MASTER_PLAN.md §1 (branch model) + §2 (merge flow) + §4 (session naming) + §5 (PR templates) + §6 (reviewer rule) + §7 (lead responsibilities). The amendment must be consistent with these.
6. docs/V1_FEATURE_SPEC.md — find your feature's §F{N} subsection. Quote specific acceptance-criteria bullet IDs in your §9 Acceptance gate.
7. ONE of the involved leads' .claude/agent-memory/meesell-{lead}/MEMORY.md — pick the most-involved lead based on your current FEATURE_PLAN.md's "Agent lineup" section. Read for context on the lead's review style and recent commits.

## Step 1 — Write status file (session start)

Update docs/plans/features/_status/{your-feature-slug}.yaml:

  status: IN_PROGRESS
  last_updated: <today's ISO 8601 UTC timestamp, e.g., 2026-06-10T15:00:00Z>
  notes: |
    Amendment session opened — bringing FEATURE_PLAN.md into canonical pattern v2 conformance.
    Reading _CANONICAL_PATTERN.md and current FEATURE_PLAN.md to build audit table.

DO NOT commit yet. The status file gets committed alongside the FEATURE_PLAN.md amendments in Step 7.

## Step 2 — Audit your FEATURE_PLAN.md against the canonical pattern

Run:

  grep -nE "^## " docs/plans/features/{your-feature-slug}/FEATURE_PLAN.md

For each of the 11 canonical sections (in order: Decisions, Agent lineup, Code surfaces, Documentation deliverables, Branch setup, Memory protocol, Dispatch templates, Review + iteration protocol, Acceptance gate, Risk register, Revision history), check:

- Does the section exist at the right heading level (## h2)?
- Does it use the exact heading text (no prefix numbers, no emoji, no variant wording)?
- Is its content present and non-trivial (more than a stub paragraph)?
- Is it in the right ORDER (1-11)?

Build a 6-column audit table:

| Section | Present? | Correct heading? | Correct order? | Content sufficient? | Action needed |
|---|:-:|:-:|:-:|:-:|---|
| 1. Decisions | ... | ... | ... | ... | ... |
| 2. Agent lineup | ... | ... | ... | ... | ... |
| 3. Code surfaces | ... | ... | ... | ... | ... |
| 4. Documentation deliverables | ... | ... | ... | ... | ... |
| 5. Branch setup | ... | ... | ... | ... | ... |
| 6. Memory protocol | ... | ... | ... | ... | ... |
| 7. Dispatch templates | ... | ... | ... | ... | ... |
| 8. Review + iteration protocol | ... | ... | ... | ... | ... |
| 9. Acceptance gate | ... | ... | ... | ... | ... |
| 10. Risk register | ... | ... | ... | ... | ... |
| 11. Revision history | ... | ... | ... | ... | ... |

The audit table goes in your final report (Step 8) — keep it open in scratch.

Also list any AD-HOC top-level sections that are NOT among the 11 (e.g., "Sprint plan", "Status preamble", "Operating context") — these need relocation (Step 3 below).

## Step 3 — Draft amendments

For each section needing action, apply ONE of these treatments:

### Case A: Canonical section is MISSING entirely

Author it from scratch using:
- Current plan content that fits the section's purpose
- Feature-specific knowledge from your lead memories
- V1_FEATURE_SPEC.md for acceptance criteria and scope locks

Be substantive — minimum content guidelines per the 4 universal-gap sections (Step 4 has full templates):
- Review + iteration protocol: ≥80 lines (per-specialist review criteria, re-dispatch failure modes, iteration cap)
- Acceptance gate: ≥40 lines (checkbox list — every condition for "feature is done")
- Risk register: ≥60 lines (3-5 risks in table format with mitigations)
- Revision history: short table (initial 2 rows for v1 + v2)

### Case B: Section is OUT OF ORDER

Move it to the canonical position. Preserve content verbatim — do NOT rewrite while relocating. The reviewer must be able to diff the move from the rewrite.

### Case C: Section has WRONG HEADING TEXT

Examples and corrections:

  Wrong: ## 1. Decisions               → ## Decisions
  Wrong: ## Decisions (Locked)         → ## Decisions
  Wrong: ## ⚠️ Mandatory read declaration → either delete (if covered elsewhere) or rename
  Wrong: ## AGENT LINEUP                → ## Agent lineup
  Wrong: ## Dispatch Templates          → ## Dispatch templates

Rename to canonical text exactly. Capitalization, no emoji, no parenthetical, no numeric prefix.

### Case D: Section is at WRONG DEPTH

Specifically inside `## Dispatch templates`: each specialist subsection MUST be `### h3`, NOT `## h2`. If a v1 plan used `## meesell-auth-builder` (h2), demote to `### meesell-auth-builder` (h3). This is the most common v1 error per the audit.

### Case E: Ad-hoc sections not in the 11

Choose ONE of:
1. Demote to a `###` subsection inside the most-relevant canonical section.
2. Move to a sibling file `docs/plans/features/{slug}/<NAME>.md` and reference it from the relevant canonical section.

Do NOT delete content — preserve it somewhere. Common ad-hoc sections observed in v1 plans and their relocation guidance:

- "Sprint plan" → `### Sprint plan` subsection inside `## Agent lineup` OR sibling file `SPRINT_PLAN.md`
- "Status preamble" / "Operating context" → preserve as preamble PARAGRAPH before `## Decisions` (not a heading; just prose at the top of the file under the title)
- "Audit findings" → sibling file `AUDIT_FINDINGS.md`
- "Mandatory read declaration" → if it duplicates Step 0 of the PLANNING_DISPATCH.md, delete; otherwise relocate to a `###` subsection inside `## Documentation deliverables`

## Step 4 — Author missing sections (the 4 universal gaps)

ALL 9 V1 plans were missing these 4. You MUST author them now even if briefly. Each must hit the minimum content threshold from Step 3 Case A.

### Section 8: Review + iteration protocol

For EACH specialist named in your §2 Agent lineup, define a `### {specialist-slug}` subsection containing:

- **Pre-approval checklist** — feature-specific (NOT generic). Examples by feature:
  - auth-otp / meesell-auth-builder: "Lua rotation uses EVALSHA with EVAL fallback on NOSCRIPT (NOT MULTI/EXEC); HMAC lookup uses secrets.compare_digest (NOT ==); access JWT TTL reads ACCESS_TOKEN_TTL_SECONDS env var (NOT hardcoded); cookie has Path=/api/v1/auth + SameSite=Strict + HttpOnly + Secure"
  - catalog-form / meesell-api-routes-builder: "Autosave PATCH uses per-IP rate limit only (NOT per-user); 5-min audit coalescing fires once per IP per 5 minutes; assert_product_ownership called before any read or write"
  - xlsx-export / meesell-data-engineer: "Template version matches Meesho 2026Q2 schema; columns A-AZ generated via openpyxl get_column_letter (NOT manual chr(65+i)); blocked-on-quality-fail check fires before any row write"
- **PR-template gate** — `.github/PULL_REQUEST_TEMPLATE/{group}.md` reference
- **Re-dispatch triggers** — 3-5 specific failure modes that make the lead reject. Be concrete (quote contract violations, not abstract concerns).
- **Re-dispatch prompt shape** — template: original dispatch + preamble "Previous run failed on X; fix Y by reading Z (specific file + section)"
- **Iteration cap** — Suggested: 3. Third re-dispatch automatically triggers a founder consult.

### Section 9: Acceptance gate

Build a checklist that captures "feature is done overall":

  - [ ] Each specialist's PR (`feature/{slug}/{group}` → `feature/{slug}`) merged
  - [ ] Integration tests green (paste the actual test command — e.g., `cd backend && pytest tests/integration/test_{slug}.py -v`)
  - [ ] Documentation deliverables landed (cross-reference §4 — list specific files)
  - [ ] V1_FEATURE_SPEC.md §F{N} acceptance criteria met — QUOTE the specific bullet IDs (e.g., "§F1.AC1 — Send OTP responds 200 within 2s; §F1.AC2 — Verify OTP issues access JWT + refresh cookie")
  - [ ] CI gates 1-5 green on feature integration branch (lint, typecheck, unit tests, integration tests, build)
  - [ ] Founder approval on the feature/{slug} → develop PR

### Section 10: Risk register

3-5 risks specific to your feature. Format:

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | <risk> | Low/Medium/High | Low/Medium/High | <mitigation, with file or section reference> |

Feature-specific risk starter list (pick what applies, write your own if your feature is different):

- auth-otp: MSG91 staging credit exhaustion; Lua EVAL incompatibility with older Valkey; HMAC pepper rotation breaking live sessions; cookie domain mismatch dev↔staging; FE refresh storm on network flap
- smart-picker: Gemini rate limit during burst; pg_trgm fallback latency under load; category tree cache staleness
- catalog-form: autosave race conditions; per-IP rate limit collisions on shared NAT; draft-recovery TTL drift
- ai-autofill: invalid-enum bypass via prompt injection; Gemini cost spike during runaway autofill; fallback-offered=true UX confusion
- image-precheck: rembg drift between dev/staging; GCS quota exhaustion; watermark prompt regression
- live-preview: stale-while-revalidate desync; ETag busting on schema version bump; preview-vs-final divergence
- price-calculator: HSN-GST mapping gaps for new categories; rounding-error compounding; weight-band miscalculation
- tracking-dashboard: N+1 query under load; pagination cursor drift on parallel product PATCH; profile completeness lag
- xlsx-export: Meesho template schema drift breaking compliance; openpyxl column-letter overflow at category-id 26+; signed-URL TTL collision with large exports

### Section 11: Revision history

Table format with one initial row + one row for this amendment:

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-10 | mesell-{slug}-planning-session-1 | Initial planning session — FEATURE_PLAN.md authored |
| v2 | <today's ISO date> | mesell-{slug}-amendment-session-1 | Pattern conformance — 4 missing canonical sections added (Review + iteration protocol, Acceptance gate, Risk register, Revision history); headings normalized; ad-hoc sections relocated per pattern v2 rules |

If your plan was authored on a different date than 2026-06-10, use the actual planning date.

## Step 5 — Verify the amended plan

After all amendments, run:

  grep -nE "^## " docs/plans/features/{slug}/FEATURE_PLAN.md

Confirm EXACTLY 11 lines printed, in this EXACT order:

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

If ANY heading doesn't match exactly (wrong text, wrong order, extra section, missing section), fix before proceeding to Step 6.

## Step 6 — Update status file (PLAN_READY)

Update docs/plans/features/_status/{slug}.yaml:

  status: PLAN_READY
  last_updated: <today's ISO 8601 UTC timestamp>
  feature_plan_line_count: <wc -l output for FEATURE_PLAN.md>
  notes: |
    Amended to canonical pattern v2 — 11 sections in locked order.
    Added 4 universal-gap sections: Review + iteration protocol, Acceptance gate, Risk register, Revision history.
    Promoted Branch setup + Memory protocol to canonical.
    Normalized headings + relocated ad-hoc sections.
    Ready for amendment PR.

DO NOT commit yet.

## Step 7 — Commit + push + open amendment PR

  git add docs/plans/features/{slug}/FEATURE_PLAN.md
  git add docs/plans/features/_status/{slug}.yaml
  # If you created any sibling .md files for relocated ad-hoc content, also add them:
  # git add docs/plans/features/{slug}/SPRINT_PLAN.md
  # git add docs/plans/features/{slug}/AUDIT_FINDINGS.md
  
  git status --short
  
  git commit -m "$(cat <<'COMMIT_EOF'
  docs(plan): amend {slug} FEATURE_PLAN.md to canonical pattern v2
  
  - Added 4 universal-gap sections: Review + iteration protocol, Acceptance gate, Risk register, Revision history
  - Promoted Branch setup + Memory protocol to canonical (per audit findings)
  - Normalized section headings + ordering
  - Relocated ad-hoc sections per pattern v2 rules
  
  Session: mesell-{slug}-amendment-session-1
  Co-Authored-By: Claude <noreply@anthropic.com>
  COMMIT_EOF
  )"
  
  git push -u origin feature/{slug}/planning

The branch ALREADY exists (it's the planning branch from the original planning PR). Your push adds a new commit on top.

If the original planning PR is already MERGED to develop, the push will not reopen that PR. In that case, open a NEW PR for the amendment:

  gh pr create --base develop --head feature/{slug}/planning \
    --title "docs(plan): amend {slug} FEATURE_PLAN.md to canonical pattern v2" \
    --body "$(cat <<'PR_BODY_EOF'
  ## Summary
  
  Brings docs/plans/features/{slug}/FEATURE_PLAN.md into conformance with the canonical pattern v2 locked at docs/plans/features/_CANONICAL_PATTERN.md.
  
  ## What changed
  
  - Added 4 universal-gap sections: Review + iteration protocol, Acceptance gate, Risk register, Revision history
  - Promoted Branch setup + Memory protocol to canonical (audit-driven)
  - Normalized section headings + ordering
  - Relocated ad-hoc sections per pattern v2 rules
  
  ## Reviewer reminder
  
  **Reviewer rule (locked 2026-06-10):**
  - For `feature/{name}/{group}` → `feature/{name}` PRs: the lead agent for this group is the reviewer.
  - For `feature/{name}` → `develop` PRs: the founder is the reviewer.
  
  This PR targets develop. **Founder is the reviewer.**
  
  ## Session
  
  - Session name: mesell-{slug}-amendment-session-1
  - Branch: feature/{slug}/planning
  - Worktree: /tmp/mesell-wt/{slug}
  PR_BODY_EOF
  )"

After PR opens: update docs/plans/features/_status/{slug}.yaml ONE MORE TIME — set status: IN_REVIEW, populate pr_number and pr_url. Stage + amend the commit OR push a follow-up commit `docs(plan): update {slug} status — IN REVIEW with PR link`.

## Step 8 — Final report (returned to founder)

Print this report to the chat:

  AMENDMENT COMPLETE — {slug}
  
  Audit findings (sections needing action before amendment):
  <paste your Step 2 audit table>
  
  Sections added (the 4 universal gaps):
  - Review + iteration protocol: <N> lines
  - Acceptance gate: <N> lines
  - Risk register: <N> risks documented in <M>-line table
  - Revision history: initial 2 rows (v1 + v2)
  
  Sections relocated or renamed:
  <list of changes — e.g., "## 1. Decisions → ## Decisions", "## meesell-auth-builder (h2) → ### meesell-auth-builder (h3 inside ## Dispatch templates)">
  
  Ad-hoc sections preserved (and where):
  <list — e.g., "Sprint plan → ### Sprint plan subsection inside ## Agent lineup">
  
  Final plan structure (11 ## headings):
  <paste the grep ^## output verified in Step 5>
  
  Files touched:
  - docs/plans/features/{slug}/FEATURE_PLAN.md (was N lines → now M lines)
  - docs/plans/features/_status/{slug}.yaml (IN_REVIEW with PR link)
  - <any sibling .md files for relocated content>
  
  PR opened: #<number> — <URL>
  
  Status: PLAN_READY → IN_REVIEW (awaiting founder merge)
  
  Memory appended: <path to your lead's MEMORY.md with session-close entry>

## Hard constraints (must NOT violate)

- DO NOT touch any other feature's FEATURE_PLAN.md
- DO NOT touch _CANONICAL_PATTERN.md or _AMENDMENT_DISPATCH.md (these are governance — only the master Director session amends them)
- DO NOT touch any other _status/*.yaml
- DO NOT touch FEATURE_PLAN.md content beyond the prescribed amendments — preserve all D-numbered decisions, all agent assignments, all code surfaces verbatim. ONLY add/relocate per pattern v2.
- DO NOT touch any lead spec (.claude/agents/meesell-*.md), PR template (.github/PULL_REQUEST_TEMPLATE/*), or MASTER_PLAN
- DO NOT touch backend/, frontend/, k8s/, infra/, terraform/, data/, themes/
- DO NOT do parallel git operations — your worktree is yours; the master tree may be operating on other branches concurrently
- DO NOT merge the PR — founder reviews and merges
- DO NOT touch feature_planning_master.md — the master session regenerates that from _status/*.yaml
```

---

## What happens after all 9 amendments are merged

Once all 9 amendment PRs are merged to develop:

1. Every FEATURE_PLAN.md conforms to pattern v2 — `grep -nE "^## " ...` returns exactly 11 lines in the locked order for all 9 features.
2. The master Director session aggregates the 9 `_status/{slug}.yaml` files and regenerates `feature_planning_master.md` reflecting the new state.
3. The coding-stage dispatches (one per specialist per feature) reference the now-conformant `FEATURE_PLAN.md` files. The dispatch prompts inside `## Dispatch templates` are paste-able as authored.
4. This amendment dispatch (`_AMENDMENT_DISPATCH.md`) and the canonical pattern (`_CANONICAL_PATTERN.md`) remain in `docs/plans/features/` as the governance reference for any future feature planning sessions (post-V1).

---

## When to NOT use this dispatch

- For a NEW feature (post-V1), use the planning dispatch flow per `PLANNING_DISPATCH.md` from the START — the new planning sub-session reads `_CANONICAL_PATTERN.md` first and authors the FEATURE_PLAN.md in the conformant shape from line 1. No amendment is needed.
- For a content-level change to a FEATURE_PLAN.md that has nothing to do with pattern conformance (e.g., a founder decision overturns D3 and the plan needs a new D-row + a superseded entry), open a regular `chore/...` or `docs/...` branch from develop, edit the plan directly, and PR. Do NOT use this amendment dispatch — it is structural only.

---

## Revision history of this dispatch

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-06-10 | master Director session + meesell-backend-coordinator | Initial dispatch authored. Targets the 9 V1 feature plans for canonical-pattern v2 conformance. |
