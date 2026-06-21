# MeeSell Plan Gate (HYBRID dispatch step 1 — read-only SPEC phase)

> Adoption Step 1 (plan-gate). Reference: `docs/dev/CLAUDE_FEATURE_ADOPTION.md` §2 / §3
> ("Plan-gate (read-only SPEC phase)") and the HYBRID dispatch rule in `CLAUDE.md` (MeeSell
> ecosystem rule 7). This gate formalizes the **read-only SPEC/plan phase that happens BEFORE
> any code is written and BEFORE any worktree is created** — i.e. it sits in front of
> `docs/dev/WORKTREE_ISOLATION.md` (step 2) and `docs/dev/REVIEW_GATES.md` /
> `docs/dev/VERIFY_GATE.md` (step 3).

## Why this gate exists

On an **8GB dev box** every full rebuild (`esbuild` / `ng build`) is expensive and can deadlock.
The most painful bugs of the last cycle — the federation singleton-logout, the
`federation.manifest` worktree-port pin, the suggest GET/POST mismatch, the autofill
`product_title` vs `product_name` key, the `size_in_ltrs` 422 — were all **wrong-key / wrong-port
/ wrong-verb / broken-singleton / contract-drift** errors that could have been caught **on paper**,
before a single RAM-thrashing rebuild. The plan gate makes the cheap catch happen first:

> **No code is written, and no worktree is created, until a written SPEC has been reviewed.**

## What HYBRID step 1 produces (the SPEC)

For **code-heavy construction**, the coordinator's first job is to produce a SPEC — an
**analysis + exact edit plan with NO code and NO worktree**. The SPEC contains:

1. **Goal** — one paragraph: what changes and why (link the founder ask / board row / bug memo).
2. **Exact files to touch** — absolute paths, each marked `edit` / `new` / `delete`. No others.
3. **Per-file edit plan** — what changes in each file, described in prose, not code. Enough that
   a reviewer can spot a wrong key / wrong path / wrong verb without seeing a diff.
4. **Contract points** — every FE↔BE seam the change crosses: HTTP **verb**, route path, request
   **field names**, **enum** values, and the matching FastAPI route / Pydantic schema. (This is
   the single highest-value section — it catches the suggest-405 / autofill / `size_in_ltrs` class.)
5. **Federation / singleton impact** (frontend) — does it touch a shared `@mesell/*` lib, a
   `federation.config.js` `mesellShared` block, the manifest, or a port? If so, name the
   `MESELL_SHARED_VERSION` / `singleton: true` invariant it must preserve.
6. **Flag gating** — any Razorpay-live or held-google-auth surface must name the feature flag.
7. **Migration plan** (if DB) — new revision, up/down, and the disposable `TEST_DATABASE_URL`
   it will be verified against (never the live dev DB).
8. **Verify plan** — the exact `/verify` assertion this change will be held to in step 3
   (change-type → assertion, per `docs/dev/VERIFY_GATE.md`).
9. **Constraints check** — READ-ONLY scraper egress, zero-spend, never-go-live, `user_id` /
   tenant scoping, no committed secrets.

The SPEC is written to the discipline's status board / coordinator memory — **never left in
throwaway chat** (same rule as the review gates).

## The gate

The SPEC is **reviewed by the session/founder BEFORE step 2**:

| Step | Actor | Output | Worktree? | Code? |
|---|---|---|---|---|
| **1 — Plan gate** | coordinator produces SPEC; session/founder reviews | reviewed SPEC | **no** | **no** |
| 2 — Build | named specialist (isolated worktree) | `feature/{slug}/{group}` PR | yes | yes |
| 3 — Review/verify | coordinator runs `/code-review` + `/verify` | merge-gate decision | n/a | n/a |

Rules:

- **Step 2 is not dispatched until the step-1 SPEC passes review.** A failed SPEC review costs
  zero RAM and zero rebuild — it is rejected back to the coordinator to re-plan, not to a builder.
- Review the SPEC against sections 1–9 above. The contract-points and federation/singleton
  sections are mandatory for any FE↔BE or federation change — a SPEC missing them is incomplete.
- The SPEC's "exact files to touch" list is the **scope contract**: if the builder needs to touch
  a file not listed, it returns to step 1, it does not silently widen scope.

## When the plan gate applies

- **Code-heavy construction** (feature code, extractions, AI-pipeline code, auth/backend changes,
  Angular components/services/styling, migrations): **plan gate is mandatory** — it is HYBRID
  step 1 and precedes the worktree.
- **Docs, status flips, ruling landings, chores**: **single-agent fast mode** — the coordinator /
  standalone lead executes directly, **no SPEC ceremony** (same carve-out as the HYBRID rule).
- **Standalone leads** (`meesell-infra-builder`, `meesell-legal-writer`) have no specialists and
  execute directly; they still self-plan for blast-radius-heavy infra changes (state the playbook
  section + rule before executing) but do not run the 3-step coordinator dance.

## Relationship to the other gates

The plan gate is the **first** of the three HYBRID gates and the cheapest:

1. **Plan gate (this doc)** — step 1, read-only SPEC, no worktree, no RAM. Catches wrong-key /
   wrong-port / wrong-verb / singleton / contract errors on paper.
2. **Worktree isolation** (`docs/dev/WORKTREE_ISOLATION.md`) — step 2, the specialist builds in
   an isolated worktree off `origin/develop`; one build-specialist worktree at a time.
3. **Review + verify** (`docs/dev/REVIEW_GATES.md`, `docs/dev/VERIFY_GATE.md`) — step 3, the
   coordinator runs `/code-review` (+ `/security-review`) and `/verify` on the specialist PR.

Catching an error in step 1 is orders of magnitude cheaper than catching it in step 3 (after a
build) or in production. Plan first.
