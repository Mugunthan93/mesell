---
name: meesell-hybrid-dispatch-rule
description: Founder-ruled 2026-06-11 — hybrid agent hierarchy; full spec→build→review for code-heavy work, single-agent fast mode for chores
metadata:
  type: feedback
---

**Rule:** MeeSell dispatching uses the HYBRID hierarchy (founder ruling "hybrid ok", 2026-06-11):

- **Code-heavy construction** (feature extractions Wave 2+ / SP04-06, AI Features 2/4/5, dual-pepper, any substantive backend/frontend code): THREE-step dispatch — (1) coordinator agent produces the task SPEC, (2) master dispatches the named SPECIALIST (sonnet builders: angular-component-builder, auth-builder, etc.) with that spec, (3) coordinator agent runs the MERGE-GATE REVIEW on the specialist's PR. Restores the specialist layer that dispatched coordinators can't reach (they have no Agent tool).
- **Docs, status flips, rulings landings, chores**: single-agent fast mode (coordinator/lead executes directly) — unchanged.

**Why:** Founder observed coordinators doing all work themselves ("all the work done by you only not the meesell agent"). Root cause: dispatched coordinator agents have no Agent tool, so the specialist layer was silently skipped. Hybrid restores genuine separate review where bugs live, keeps speed where ceremony is waste. ~+15-25 min per code task, roughly cost-neutral (construction moves opus→sonnet).

**How to apply:** Every master dispatch decision: ask "is this substantive code construction?" If yes → 3-step. If docs/status/chore → fast mode. Wave 2 (SP04/SP05) onward. Coordinator review at step 3 must be a REAL gate (can reject back to specialist).
---
name: meesell-hybrid-dispatch-rule
description: CLAUDE.md Rule 7 — hybrid dispatch for MeeSell agents (founder-ruled 2026-06-11). Three-step for code-heavy work; single-agent for docs/chores.
metadata:
  type: feedback
---

# MeeSell Hybrid Dispatch Rule (CLAUDE.md Rule 7)

**Ruled by founder 2026-06-11. Added as Rule 7 in CLAUDE.md.**

## The Rule

Dispatched coordinator agents have no Agent tool — they cannot reach their specialists. The session window must run the hierarchy FOR them:

**Code-heavy construction** (feature code, extractions, AI pipeline code, auth/backend changes):
THREE-step dispatch:
1. Dispatch the **coordinator** to produce a task SPEC
2. The **session** dispatches the named **specialist** agent (the sonnet builders) with that spec
3. Dispatch the **coordinator** again to run the MERGE-GATE REVIEW on the specialist's PR (real gate — can reject back)

**Docs, status flips, rulings landings, chores**:
SINGLE-AGENT fast mode — the coordinator/lead executes directly. No ceremony.

**Standalone agents** (`meesell-infra-builder`, `meesell-legal-writer`): no specialists — always execute directly.

**Why:** Coordinator agents (opus) cannot spawn sub-agents (no Agent tool in their tool tier). The session must bridge them to their specialists. Without this, coordinators were either doing specialist work themselves OR the specialist work was never dispatched.

**How to apply:** Before every MeeSell dispatch, classify: is this code-heavy construction or docs/chores? Code → three-step; docs → single. The classification determines the dispatch shape for the entire task.
