---
name: meesell-not-using-nexus
description: MeeSell runs its own 19-agent meesell-* fleet, NOT the Nexus SDLC pipeline — do not assume Nexus coverage when assessing tooling/process for MeeSell
metadata:
  type: project
---

MeeSell does NOT use the Nexus SDLC framework/pipeline for project work — even though this session runs through the Nexus Director at the workspace level and `.nexus/` artifacts (logs, director memory dir) exist.

**Why:** Founder confirmed (2026-06-21) while reviewing the Claude-skills productivity report, which had wrongly assumed Nexus coverage and under-scored prompt-skills (e.g. Karpathy Skills was capped as "redundant with Nexus SDLC"). MeeSell instead runs a dedicated fleet of 19 `meesell-*` agents: coordinator→specialist HYBRID dispatch (coordinator writes a SPEC → named specialist builds → coordinator runs a merge-gate review), decentralized per-agent file memory (`.claude/agent-memory/meesell-*/MEMORY.md`), locked spec docs, STATUS files, the git worktree flow (`feature/{slug}/{group}`→integration→develop, founder merges), and code-enforced PreToolUse hooks.

**How to apply:** When assessing tooling or process fit for MeeSell, evaluate overlap against the `meesell-*` fleet, NOT Nexus. There is no `nexus:discover`, no Nexus staged dispatch, and no Nexus SDLC gates in MeeSell. Behavioral prompt-skills like Karpathy's "Surgical Changes" / "Think Before Coding" are NOT redundant here and fill real gaps. Related: [[project_meesell_session3_state]].
