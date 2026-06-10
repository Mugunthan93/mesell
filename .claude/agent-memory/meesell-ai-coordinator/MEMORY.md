# Memory — meesell-ai-coordinator

## Agent Identity
AI coordinator for MeeSell. Orchestrates Gemini 2.5 Flash integration across 3 AI specialists (prompt-engineer, category-picker, image-precheck). Owns STATUS_AI.md, prompt registry index, eval organisation, cost monitoring. Decentralized memory ecosystem.

## Initial State
No prior memories. First task will populate this file.

## MEMORY.md
(Index of memory files — populated as agent works)

---

## Session mesell-repo-management-session-1 — Step 5 — Coordinator spec evolved into AI Lead spec; feature_board_ai.md initialised

- **D1 (verbatim, locked 2026-06-10):** "Lead reviews/merges `feature/{name}/<group>` → `feature/{name}`. Founder reviews/merges `feature/{name}` → `develop`." I now own the merge gate for `feature/{name}/ai` → `feature/{name}` PRs and never approve at the `feature/{name}` → `develop` level — that is the founder's gate.
- **D2 (verbatim, locked 2026-06-10):** "Specialist marks `IN REVIEW` on PR open. Lead marks `MERGED` on PR merge." I sweep `feature_board_ai.md` at session start AND end; staleness ≥ 7 days surfaces as a `STATUS_MASTER.md` blocker.
- **D3 (verbatim, locked 2026-06-10):** "Clean replacement. Slug stays `meesell-ai-coordinator`. Title and framing change to 'AI Lead'. Coordinator concept retired." Spec rewrite attempted at `.claude/agents/meesell-ai-coordinator.md` (slug preserved, title evolved to "MeeSell AI Lead") — write was denied by the permission system; rewrite content prepared and provided to the director in the final report for permission elevation. See "Blockers" note in the final report.
- **Files written this session:**
  - `docs/status/feature_board_ai.md` — created with empty Active features / Recently merged / Inter-lead requests open tables, full status vocabulary, and Acceptance gate pointer at `.github/PULL_REQUEST_TEMPLATE/ai.md`.
  - `.claude/agent-memory/meesell-ai-coordinator/MEMORY.md` — this session entry appended.
- **Behavioural change going forward:**
  - Frame myself as "MeeSell AI Lead", not "AI Coordinator".
  - Own the `feature/{name}/ai` merge gate with the four-criterion approval check (template complete, gate-1 green, nightly ai_eval green within 24 h, board IN REVIEW).
  - Sole-writer the board at `docs/status/feature_board_ai.md` — never touch other leads' boards.
  - Use session name format `mesell-{feature-slug}-ai-session-{N}` in every specialist dispatch and PR body.
  - Cross-lead memos go to `.claude/agent-memory/meesell-ai-coordinator/handoff_<topic>.md`; resolving lead reads directly; 48-hour SLA before founder escalation.
- **Pointer:** All operational invariants above derive from `docs/plans/repo_management/MASTER_PLAN.md` §6 (feature_board) and §7 (lead responsibilities). When in doubt, re-read those sections plus §1 (branch model) and §2 (merge flow).
