---
name: feedback-ai-coordinator-specialist-dispatch
description: AI coordinator must dispatch its 3 specialists as separate Agent() calls — never execute specialist work directly as lead
metadata:
  type: feedback
---

**Rule:** When dispatching `meesell-ai-coordinator`, always verify it uses `Agent()` calls to dispatch each specialist (`meesell-prompt-engineer`, `meesell-category-picker-builder`, `meesell-image-precheck-builder`). The coordinator must NOT execute specialist-scope work directly.

**Why:** Founder explicitly requires pure specialist-dispatch discipline. In session `mesell-ai-track-session-1` (2026-06-11), the coordinator executed mechanical edits directly because its sub-session tried the `Task` tool (async background — not available in agent context) instead of the `Agent` tool (synchronous subagent dispatch — IS available). The work was correct but the process was wrong.

**How to apply:**
- In the coordinator's dispatch prompt, explicitly instruct: "Use the `Agent` tool (NOT the `Task` tool) to dispatch each specialist. `Task` is not available in subagent contexts; `Agent` is."
- Add a per-specialist dispatch section to the coordinator prompt with clear `Agent(subagent_type="meesell-<specialist>", ...)` instructions.
- If the coordinator's session-end report says "dispatched X directly" instead of "dispatched Agent(meesell-X)", that's a violation — note it and enforce correction on the next dispatch.
- The coordinator is a lead, not a builder. It gates, coordinates, and dispatches. Specialist-scope authoring (prompt templates, fixture files, eval runners) belongs to the specialists.
