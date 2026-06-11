# Legal Track — Session Dispatch Brief

**Session name:** `mesell-legal-track-session-1`
**Date authored:** 2026-06-11 (master session, founder-approved track launch)
**Status:** READY — track was 🔴 Not started; 3 founder decisions are collected IN THIS SESSION as step 1

---

## What this session is

You are a dedicated sub-session for the MeeSell **Legal & Marketing track**. Your job is to (1) collect the 3 outstanding founder decisions, then (2) dispatch `meesell-legal-writer` to produce the V1 legal + compliance + marketing copy pack.

**Only `meesell-*` agents may execute MeeSell work.** `meesell-legal-writer` has NO Bash — it authors documents only; THIS session window performs all git operations on its behalf.

## Required reading (in order, before any dispatch)

1. `CLAUDE.md` (project root) — ecosystem rules
2. `docs/LEGAL_AND_COMPLIANCE_INFO.md` — the locked reference doc; **§10 lists the founder decisions**
3. `docs/PRICING_LOCKED.md` — plan tiers ₹499–1,999/mo (refund policy must match)
4. `docs/plans/repo_management/MASTER_PLAN.md` — Model C git conventions (v1.1)
5. `docs/status/STATUS_LEGAL.md` — current (empty) track state
6. `.claude/agent-memory/meesell-legal-writer/MEMORY.md` — writer's own memory
7. `docs/V1_FEATURE_SPEC.md` Feature 1 (auth) — the DPDP consent flow the privacy policy must describe (AS-BUILT 2026-06-11, PR #46)

## Step 1 — Founder decisions (DO THIS FIRST, in plain language, one at a time)

Present LEGAL_AND_COMPLIANCE_INFO.md §10 to the founder and record his rulings. The 3 known-outstanding ones:

1. **Entity type** — proprietorship vs LLP vs Pvt Ltd (affects ToS party, Razorpay KYC pack, GST registration)
2. **GST timing** — register now vs at threshold (affects invoicing language + pricing display)
3. **Business name** — lock the legal trading name (appears on every document)

Tick the chosen options in §10 (additive edit, no restructure) and record the rulings on STATUS_LEGAL.md. If §10 contains more open decisions than these 3, surface them all.

## Step 2 — Dispatch `meesell-legal-writer`

Deliverables (per its agent spec, grounded in the §10 rulings):

- **Legal pack**: Privacy Policy (DPDP-compliant, matches the AS-BUILT consent flow + HttpOnly-cookie/JWT auth model), Terms of Service, Refund/Cancellation Policy (must match PRICING_LOCKED.md tiers + Razorpay Subscriptions), Cookie Policy, DPA
- **Razorpay KYC pack** — checklist + drafted descriptions for the chosen entity type
- **GST pack** — per the GST-timing ruling
- **Email templates** — transactional set (OTP is SMS via MSG91; these are lifecycle emails)
- **Landing copy** — Tirupur-seller-first voice, simple English + Tamil-friendly phrasing

Output location: `docs/legal/` (create). Marketing copy: `docs/marketing/`.

## Git conventions (Model C — this session runs git for the writer)

- ALL branch work in worktrees under `/tmp/mesell-wt/` — NEVER switch the master tree's branch.
- Integration branch `feature/legal-v1/integration` (F1); group branch `feature/legal-v1/legal`.
- Group → integration: SQUASH merge, gate decision as PR comment, `--admin`.
- Integration → develop: **FOUNDER-ONLY** (§2.2) — open `[FOUNDER GATE — DO NOT MERGE]` and leave open. The founder is IN this session, but the merge still goes through the gate PR (he can delegate the CLI merge in-session).
- `--delete-branch` worktree gotcha: merge lands, local cleanup fails — delete remote ref via `gh api -X DELETE`, then `git worktree remove`.
- Explicit-path staging only.

## Hard constraints

- **No legal advice posture**: every document carries the "review with a lawyer/CA before reliance" banner per LEGAL_AND_COMPLIANCE_INFO.md's own caveat.
- **No invented facts**: rupee figures, entity details, addresses come from the founder's §10 rulings or are left as clearly marked `[FOUNDER: fill]` placeholders — never fabricated.
- **Memory**: writer appends to its own memory only (this session writes the file for it if needed, into `meesell-legal-writer/` only).
- **Parallel tracks live**: frontend MF, infra CI, and AI sessions may be running. Touch ONLY `docs/legal/`, `docs/marketing/`, `docs/status/STATUS_LEGAL.md`, LEGAL_AND_COMPLIANCE_INFO.md §10 ticks, and the writer's memory.

## Session end

Update `STATUS_LEGAL.md` + writer memory. Report to the founder: rulings recorded, documents produced, the founder-gate PR number, and any `[FOUNDER: fill]` placeholders awaiting real-world data (PAN, address, etc.).
