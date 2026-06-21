---
name: token-economy
description: Use when managing context/token budget across a session or multi-agent dispatch — when many skills or agents are loaded, when the context window is filling, when deciding whether to read files directly or delegate the read, or when a long session risks quality decay. Optimizes tokens-per-task WITHOUT degrading output quality. NEVER use it to make output terse — quality is a hard constraint, not the variable.
---

# Token Economy

## Principle: optimize tokens-per-task, never quality
Quality — correctness, clarity, completeness, verification, citation — is a HARD constraint. Token cost is the variable you minimize *subject to* that constraint. Never trade away correctness, edge-case handling, source citations, or verification steps to save tokens. Explicitly REJECT terseness-for-its-own-sake (e.g. "Caveman"-style output compression): cutting quality to cut tokens is forbidden here.

## The biggest lever: delegate reads to subagents; keep conclusions, not dumps
When answering means sweeping many files/dirs, dispatch a subagent (fork/Explore/general-purpose) to do the reading and return only the conclusion. The file contents never enter the main context — you keep the 200-token answer, not the 20,000-token dump. This is the single largest saving and it PRESERVES quality (the work still happens, just off the main thread). Once delegated, don't also do the search yourself.

## Progressive disclosure
- Rely on on-demand loading: skills load full SKILL.md only when invoked; only their one-line descriptions are always in context. Having many skills installed is cheap — do not remove skills to save tokens.
- Read the slice you need: use Read offset/limit; prefer Grep/Glob to locate before reading whole files. Don't re-read a file you just edited.

## Prompt-cache economics (5-minute TTL)
- The Anthropic prompt cache has a ~5-min TTL. Batch related work so cached context stays warm; cache hits are ~10x cheaper.
- Avoid idle gaps that bust the cache. If you must wait, either stay under ~270s (cache warm) or commit to a longer wait and accept one cache miss — don't pick the worst-of-both ~5-min mark.

## Compaction & handoff discipline
- Use `/context` to see where tokens go (system prompt, tools, skills, memory, history).
- `/compact` before critical work to summarize+shrink history.
- Hard rule: if remaining budget drops below ~20K tokens, save session-state and start a fresh window rather than silently degrading quality. Surface the constraint; never quietly cut corners as context fills.

## Memory retrieval triage (3 levels — stop when sufficient)
1. Scope-filter (project + type + recency) → ~50 candidates.
2. Relevance-rank → top 5 only.
3. Lazy-load full detail only if needed. Never dump raw memory into context.

## Multi-agent / 8 GB-fleet specifics
- Each dispatched agent has its OWN context budget — push large reads/builds into agents to keep the orchestrator lean.
- Prefer pipeline over barrier so fast items don't wait on slow ones.
- Builds are one-at-a-time on the 8 GB box; the dashboard/env-manager reads state read-only (no extra build cost).

## Quality guardrails — NEVER skip these to save tokens
- verification-before-completion (run the check, show evidence) is not optional.
- The coordinator merge-gate review and the VERIFY gate stay in force.
- source-driven-development citations stay in force.

## Anti-patterns
| Thought | Reality |
|---|---|
| "I'll make responses terse to save tokens" | Terseness ≠ economy. Cutting quality is forbidden; cut *redundant context*, not *answer quality*. |
| "The context window is huge, I'll fill it" | Window size ≠ attention budget. Focused context outperforms large context. |
| "I'll read all these files myself" | Delegate the sweep to a subagent; keep the conclusion, not the dump. |
| "Remove skills to save context" | Skills are progressively disclosed — installed ≠ loaded. Removing them saves almost nothing. |
| "I'll skip verification this once to save tokens" | Quality is the hard constraint. Never. |
