# Claude Skills Productivity Analysis
*Generated: 2026-06-21 | Team: MeeSell | Stack: FastAPI · Angular 18 · GCP · K3s*

## Executive Summary

Of the 12 skills researched, one product (HyperFrameworks) does not exist and should be skipped entirely. The highest-ROI installs for the MeeSell stack are Skill Creator (free, Anthropic-official, directly compounds every future agent dispatch) and claude-mem (automated session memory that complements the existing 19-agent MEMORY.md architecture). Context7 delivers immediate debugging value for the Pydantic v2 + SQLAlchemy 2.0 + Angular 18 signals stack where LLM training data goes stale fastest, but its free tier is insufficient for a team and the Pro plan at $10/seat/month is required. SuperPowers and the Karpathy Skills framework both address real failure modes but largely duplicate ceremony already provided by the Nexus SDLC framework. UI UX Pro Max carries an unpatched CVSS 9.3 RCE vulnerability and should not be installed in any production development environment until the fix is confirmed merged.

## Priority Matrix

| Skill | Verdict | Productivity Score | Free Tier | Integration Method |
|-------|---------|-------------------|-----------|-------------------|
| Skill Creator | High value | 8/10 | Yes (bundled with Claude Code) | Claude Code skill/slash command |
| Context7 | High value | 7.5/10 | Yes (1,000 calls/month — insufficient for a team) | Multiple (MCP + skill) |
| claude-mem | High value | 7.5/10 | Yes (fully free, AGPL-3.0) | Multiple (MCP + hooks) |
| SuperPowers | Moderate value | 7/10 | Yes (MIT, fully free) | Claude Code skill/slash command |
| Excalidraw | Moderate value | 6.5/10 | Yes (fully free) | Multiple |
| Agent Browser | Moderate value | 6.5/10 | Yes (Apache 2.0, fully free) | Multiple |
| Ralph Loop | Moderate value | 6.5/10 | Yes (fully free) | Claude Code skill/slash command |
| Karpathy Skills | Moderate value | 6.5/10 | Yes (MIT, fully free) | Claude Code skill/slash command |
| MCP Builder | Moderate value | 6.5/10 | Yes (MIT, fully free) | Claude Code skill/slash command |
| Frontend Designer | Moderate value | 5.5/10 | Yes (fully free) | Claude Code skill/slash command |
| UI UX Pro Max | Low value | 4.5/10 | Yes (MIT, fully free) | Claude Code skill/slash command |
| HyperFrameworks | Skip | 0/10 | N/A | N/A — product does not exist |

---

## Detailed Analysis

### 1. Skill Creator — 🟢 High value

**What it is:** An official Anthropic-built Claude Code plugin that automates the full lifecycle of creating, evaluating, improving, and benchmarking custom SKILL.md slash-command files. It is a meta-skill — you use it to build and harden the other skills your agent fleet will rely on every session.

**Official URL:** https://claude.com/plugins/skill-creator

**Integration:** `/plugin install skill-creator@claude-plugins-official` inside Claude Code, then `/reload-plugins`. Many users already have it bundled as a read-only built-in in recent Claude Code releases.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | Full plugin included with any Claude subscription; bundled in Claude Code |
| No paid tier | — | Cost is purely Claude token usage during eval/benchmark runs |

#### Key Features
- Create mode: dialog-driven wizard that generates a SKILL.md with correct YAML frontmatter and instruction body
- Eval mode: define test cases (input + expected output), run them against the skill via an internal Executor agent
- Improve mode: Analyzer agent reads eval failures and proposes targeted instruction edits
- Benchmark mode: runs N iterations and reports variance for consistency measurement before shipping
- Four internal sub-agents: Executor, Grader, Comparator, Analyzer
- CI/CD integration hook for automatic eval runs on skill version publish
- Produces skills that drop into `~/.claude/skills/` or `.claude/skills/` with no extra runtime dependency

#### Productivity Impact for MeeSell (8/10)
The highest-ROI use for MeeSell is authoring 5-8 project-specific skills that encode FastAPI router conventions (UUID PKs, async handlers, HTTPException patterns), Angular 18 standalone component patterns (OnPush + signals + Tailwind + Material), and Alembic migration rules (TIMESTAMPTZ, gen_random_uuid(), JSONB indexes). Once authored, these skills fire automatically on every agent dispatch, eliminating the re-explanation overhead that currently inflates coordinator prompts. The Eval + Improve loop is uniquely valuable for the Gemini catalog-generation pipeline where prompt quality directly determines cost against the ≤₹0.05/call ceiling.

#### Use Cases for MeeSell
- Codify FastAPI router conventions so every `meesell-api-routes-builder` dispatch auto-applies them without re-prompting
- Author an Angular standalone component skill encoding OnPush + signals + Tailwind + Material so `meesell-angular-component-builder` never produces NgModule-style output
- Build a K3s deployment checklist skill gating every infra change through the 8-point cloud-deploy-check automatically
- Use Eval + Benchmark modes to measure variance in `meesell-prompt-engineer` output before promoting a new Gemini prompt to staging — directly addressing the smart-picker cost/quality tradeoffs already in memory
- Author a Razorpay + MSG91 integration skill so auth-related dispatches never miss the JWT-in-memory / refresh-cookie / Valkey allowlist pattern from Decision #14
- Write a Gemini prompt-engineering skill tuned to the catalog text pipeline (Flash model, JSON output shape, ≤₹0.05/call ceiling)

#### Limitations & Risks
- Bundled version is read-only — cannot be edited in place; must override by dropping your own SKILL.md with the same name in the skills directory (non-obvious, documented in GitHub issues #911 and #9954)
- Skills are injected as a single static context block at session start; Claude Code does not re-read the SKILL.md on later turns — dynamic or stateful skills are not possible within a session
- Skill triggering is probabilistic: Claude decides whether to consult a skill based on description match; simple one-step queries may not trigger it even if description matches
- Eval mode is not a formal test framework — no structured assertion library, no diff tooling; Grader agent scoring is itself non-deterministic
- Productivity gain is conditional on the team committing to skill authoring and maintenance — teams that skip authoring get zero value

#### Alternative
`claude-code-skill-factory` (github.com/alirezarezvani/claude-code-skill-factory) for template generation at scale. `flashingcursor/skill-creator-plugin` is a community fork with fewer read-only constraints if the bundled version's immutability is a blocker.

---

### 2. Context7 — 🟢 High value

**What it is:** A third-party MCP server (built by Upstash) that injects up-to-date, version-specific library documentation into AI coding prompts. It solves LLM hallucination of deprecated or non-existent APIs by fetching current docs from a registry of 33,000+ libraries at query time.

**Official URL:** https://context7.com

**Integration:** `npx ctx7 setup --claude` — authenticates via OAuth device flow, installs MCP server config and Claude Code skill in one command. API key stored in `CONTEXT7_API_KEY`.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | 1,000 API calls/month (cut from ~6,000 in January 2026); 20 bonus calls/day after limit |
| Pro | $10/seat/month | 5,000 calls/seat/month, private repo access, team collaboration, additional calls at $10/1,000 |
| Enterprise | ~$2.50–$30/user/month (volume) | SOC-2 Type II, SSO, self-hosted, dedicated SLA, up to 5,000 members |

#### Key Features
- `resolve-library-id` MCP tool — canonicalizes a library name to a Context7 ID
- `query-docs` MCP tool — fetches current version-specific documentation with optional topic focus
- `/context7:docs` slash command for manual lookup
- Auto-triggering Documentation Lookup Skill — fires when you mention a framework or library
- `docs-researcher` agent running in a separate context to keep the main thread clean
- Coverage of 33,000+ libraries including FastAPI, SQLAlchemy 2.0, Angular 18, Pydantic v2, Celery, Alembic, RxJS
- Version-aware retrieval — detects version context from prompts and serves matching docs
- `npx ctx7` CLI for docs lookup without MCP daemon

#### Productivity Impact for MeeSell (7.5/10)
The MeeSell stack — FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Angular 18 signals, Alembic async — is precisely the intersection where LLM training data goes stale fastest. SQLAlchemy 2.0's `select/execute/scalars` async API, Pydantic v2's `model_validator`/`ConfigDict` breaking changes, and Angular 18's `inject()` + standalone component APIs are documented hallucination sources that cause hours of debugging. Context7 eliminates this class of error. Score is capped at 7.5 because Gemini 2.5 Flash and GCP/K3s-specific operational docs are unlikely to be well-covered, and the free tier is insufficient for a team doing active development.

#### Use Cases for MeeSell
- FastAPI route and dependency injection patterns — prevents hallucinated parameter signatures for lifespan, background tasks, and dependency overrides
- SQLAlchemy 2.0 async session patterns — the async `select/execute/scalars` API differs significantly from 1.x
- Pydantic v2 `model_validator`, `field_validator`, and `ConfigDict` — v2 broke many v1 patterns; top hallucination risk
- Angular 18 standalone components, `provideRouter`, signals API, and `inject()` — post-training-cutoff changes for most models
- Alembic async migrations — autogenerate with async engines is a documented pain point
- Celery 5.x task API and Valkey connection patterns for image processing and generation workers
- Angular Material 18 component API — `MatDialog`, `MatSnackBar`, and reactive form integration

#### Limitations & Risks
- Free tier cut to 1,000 calls/month in January 2026 (from ~6,000) with no advance notice — insufficient for a team doing active development
- ContextCrush vulnerability (February 2026): a poisoned community-contributed library entry could inject malicious instructions into agent context; patched within 2 days but the centralized registry architecture makes this a recurring supply-chain risk
- Documentation quality is community-contributed with no automated validation — cross-library queries rated as low as 3.5/10 in some benchmarks
- Niche/internal libraries (GCP-specific modules, K3s Helm charts, Gemini 2.5 Flash Python SDK edge cases) may have incomplete coverage
- Cloud-dependent: all doc fetches go through Upstash servers — no offline mode
- `research mode` feature shipped April 24, 2026 and fully reverted May 4 — indicates some instability in new feature releases
- Competitors (Deepcon at 90% accuracy vs Context7's 65%) suggest it is not the most accurate option despite being most popular

#### Alternative
GitMCP is the best zero-cost alternative: turns any public GitHub repository into a documentation source via MCP with zero setup, reads `llms.txt`/README/docs files directly, and is fully free open-source. Docfork (MIT licensed, free tier with 1,000 calls/month, open-source) is the strongest direct competitor with better accuracy benchmarks. Combining GitMCP (for Angular, FastAPI, and GCP SDK GitHub repos) with Claude's native web search covers most use cases without paying $10/seat/month.

---

### 3. claude-mem — 🟢 High value

**What it is:** A free, open-source persistent memory plugin for Claude Code that automatically captures everything Claude does during a session via lifecycle hooks, compresses observations using Claude's agent SDK, stores them locally in SQLite + ChromaDB, and injects semantically relevant context back into future sessions — without any manual prompting.

**Official URL:** https://github.com/thedotmack/claude-mem

**Integration:** `npx claude-mem install` — single command that registers 5-6 lifecycle hooks and starts a local Bun-managed worker service on port 37777.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | Fully free, AGPL-3.0 licensed; all data stored locally in `~/.claude-mem/`; no usage limits on storage |
| No paid tier | — | Only ongoing cost is Claude API tokens for compressing observations (small background cost per session) |

#### Key Features
- Automatic session context capture via 5-6 lifecycle hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd) — zero manual work after install
- AI-powered compression: raw tool-use observations compressed into structured facts, concepts, and file references via Claude agent SDK
- Hybrid search: SQLite FTS5 for keyword/full-text search + ChromaDB vector embeddings for semantic search — all local, no external embedding API
- Progressive disclosure: returns compact 50-100 token indexes first, fetches full details only on demand — approximately 10x token savings vs naive full-load
- 4 MCP tools exposed to Claude: `mem-search`, `mem-timeline`, `get_observations`, `get_summary`
- Web viewer dashboard at `http://localhost:37777` for real-time memory visualization
- `<private>` tags to exclude sensitive content from storage
- Auto-generated CLAUDE.md activity timeline per project
- Beta Endless Mode: ~1,000 tool uses per session vs standard ~50 (adds 60-90s latency per tool invocation)

#### Productivity Impact for MeeSell (7.5/10)
MeeSell already has an elaborate manual memory system (19 agent memories in `.claude/agent-memory/`, STATUS files, handoff docs) — claude-mem directly complements this by automatically capturing what each agent actually does during sessions: debugging decisions, file paths touched, API quirks discovered. Reported community gains include 60% less time re-explaining context and session-to-feature time roughly halved. Score is capped at 7.5 because the AGPL-3.0 license requires legal review for a commercial SaaS, Endless Mode's 60-90s per-tool latency is unacceptable for fast builder agents, and the single-machine local storage does not follow agents across different worktrees.

#### Use Cases for MeeSell
- Reducing repeated context re-injection for long-running section coordinator sessions — captures agent decisions automatically instead of requiring manual handoff doc writes
- Preserving debugging discoveries across sessions (the wizard PATCH 422 root cause, the federation singleton bug chain) so the next agent session starts with that context already loaded
- Tracking which files each specialist agent actually modified during a session — complementing the existing per-agent MEMORY.md system
- Capturing Celery/Valkey/Gemini API call patterns and errors during AI pipeline development so `meesell-ai-coordinator` retains learned quirks across sessions
- Reducing token burn on repeated CLAUDE.md + locked-doc re-reads at session start by injecting only semantically relevant past observations

#### Limitations & Risks
- Single-user, single-machine only: memory lives in `~/.claude-mem/` and does not sync across machines or team members — agents running on different worktrees will not share a memory store automatically
- Stability issues as of early 2026: orphaned subprocess accumulation causing SQLite lock errors, macOS crashes, Windows CLI freeze
- AGPL-3.0 license: commercial teams must publish modified source if deployed as a network service; `ragtime/` subdirectory adds a non-commercial restriction — legal review required for a commercial SaaS
- Endless Mode (beta) adds 60-90 seconds of latency per tool invocation — prohibitive for fast builder-agent sessions
- Requires Node.js 20+, Bun runtime, uv Python package manager, and ChromaDB — adds infrastructure dependency on an already RAM-constrained 8GB dev machine
- Background worker on port 37777 is another always-on process competing for RAM/CPU alongside the existing MeeSell dev stack (backend :8001, 6 Angular remotes :4201-4206, PostgreSQL, Valkey)
- Does NOT integrate with the existing `.claude/agent-memory/` distributed memory system — it is a parallel, separate memory layer
- Privacy tag management (`<private>`) is manual — agents must be instructed to wrap sensitive data (API keys, OTP bypass codes) or it may be captured

#### Alternative
Mem0 (https://mem0.ai) — MIT-licensed, freemium (10k operations/month free tier), supports both cloud and self-hosted deployment, has a proper REST API enabling multi-agent and multi-machine memory sharing. Better fit for a team with multiple agents across worktrees and no AGPL license concern. The existing `.claude/agent-memory/` native MEMORY.md approach remains fully adequate for the current project scale as a zero-dependency baseline.

---

### 4. SuperPowers — 🟡 Moderate value

**What it is:** A free, open-source agentic skills framework (created by Jesse Vincent, not an Anthropic product) that installs 20+ composable slash-command skills into Claude Code enforcing a structured brainstorm → spec → plan → TDD → execute → review workflow. It is the second most-installed plugin in the Anthropic Claude Code marketplace with approximately 752k installs as of June 2026.

**Official URL:** https://github.com/obra/superpowers

**Integration:** `/plugin install superpowers@claude-plugins-official` inside Claude Code. Global install recommended.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | MIT-licensed; all 20+ skills included; no usage caps, no account required |
| No paid tier | — | Only cost is Claude Code token consumption (~9% net reduction on medium/complex tasks reported after optimization) |

#### Key Features
- Brainstorming skill: Socratic clarification — Claude asks what you are really building before writing a single line
- Spec self-review checklist: catches 4-5 bugs in ~30 seconds before implementation begins
- `/write-plan` and `/execute-plan`: produces a step-by-step plan for developer review, then executes against it
- Test-Driven Development (TDD): enforces red-green-refactor cycle — tests must fail first
- Subagent-driven development: breaks large tasks into parallel sub-agents with built-in merge-back
- Code review skill: evaluates produced code against the plan, coding standards, and architectural principles; can reject back to implementation
- Systematic debugging methodology: four-phase workflow requiring root cause investigation before any fix
- `/using-superpowers`: re-injects the skill framework reminder mid-session to prevent drift back to ad-hoc mode
- 20+ community and lab skills via `obra/superpowers-skills` and `obra/superpowers-lab` repos
- Multi-platform: Claude Code, Cursor, Gemini CLI, GitHub Copilot CLI, Codex, and others

#### Productivity Impact for MeeSell (7/10)
For a team without its own SDLC framework this would score 9/10. For MeeSell specifically, Superpowers' brainstorm→plan→TDD→review cycle largely duplicates what the Nexus meesell-* agent hierarchy already provides: `nexus:discover` covers brainstorming, coordinator dispatch covers planning, merge-gate coordinator review covers code review, and `meesell-test-writer` covers TDD. The highest marginal value is as a lightweight fallback for quick-fix sessions that do not warrant a full three-step Nexus dispatch, and for enforcing the four-phase debugging methodology on production issues like the `size_in_ltrs` enum validator bug or the auth refresh storm.

#### Use Cases for MeeSell
- New feature scoping when no Nexus pipeline is running — use `/brainstorm` before writing a new FastAPI router or Angular component to surface edge cases
- Enforcing TDD on backend services (pytest + httpx AsyncClient) — `/tdd` skill forces the red-green-refactor cycle that `meesell-services-builder` is supposed to follow
- Code-review gate for solo quick-fix PRs that do not warrant a full three-step Nexus dispatch
- Systematic debugging of production issues (federation singleton bug, auth refresh storm) using the four-phase root-cause methodology instead of guessing fixes
- Writing new meesell-* agent skill files using the custom skill authoring module

#### Limitations & Risks
- Duplicates Nexus SDLC ceremony: MeeSell already has brainstorm (nexus:discover), planning, dispatch, and code-review stages — the two frameworks can conflict or cause double-planning
- Token overhead is real even after the 69% compression pass: all skills inject context at session start; adds to context burn on the 8GB RAM machine already under memory pressure
- Not project-aware: no knowledge of MeeSell's agent roster, TICKETS.md, feature slugs, or branch naming conventions — all project context must still be provided manually
- No awareness of MeeSell's git worktree model, `feature/{slug}/{group}` branching, or the two-step squash-merge flow
- Community skills quality varies: `obra/superpowers-lab` is experimental; vet before using in production sessions

#### Alternative
The native `nexus:dispatch` pipeline already in use for MeeSell. For pure code-review gating, the built-in `/code-review` skill (already in the available skills list) covers the same ground without adding a new plugin dependency.

---

### 5. Excalidraw — 🟡 Moderate value

**What it is:** Excalidraw integrates with Claude Code through two distinct mechanisms: (1) an official MCP App published by the Excalidraw team (`excalidraw/excalidraw-mcp`) that streams hand-drawn interactive canvases directly into the Claude chat window; and (2) several Claude Code skills that teach Claude how to generate `.excalidraw` JSON files from natural language descriptions. These are not the same product — the official MCP is the closest to first-party; the skills are third-party community tools.

**Official URL:** https://github.com/excalidraw/excalidraw-mcp

**Integration:** Three paths. PATH 1 (recommended): add `excalidraw-mcp` via Claude.ai Connectors or `.mcp.json` with `type: http` — hosted endpoint, no local server needed. PATH 2 (no server): clone `coleam00/excalidraw-diagram-skill`, copy to `.claude/skills/excalidraw-diagram/`, run `uv sync && uv run playwright install chromium`. PATH 3 (full canvas control): clone `yctimlin/mcp_excalidraw`, build, add to `.mcp.json`.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | `excalidraw/excalidraw-mcp` fully open-source; all Claude Code skills free; no API key for diagram generation |
| Excalidraw+ (optional) | ~$7/month | Cloud save, version history, real-time collab — completely optional for the MCP/skills to function |

#### Key Features
- Official MCP App: streams hand-drawn diagrams inline in Claude chat using MCP Apps protocol; interactive fullscreen editing inside the chat window
- Skill approach (coleam00): generates `.excalidraw`, `.svg`, and `.png` files; Playwright-based visual validation loop so Claude can see its own output, detect layout issues, and self-correct
- 26 MCP tools in `yctimlin/mcp_excalidraw`: get/clear/export/import/duplicate/snapshot/describe/screenshot scene; real-time canvas sync
- Natural language to diagram: describe the architecture and Claude generates a fully editable `.excalidraw` file
- Architecture codebase auto-scan: Claude Code can analyze an existing repo and auto-generate an architecture diagram
- Semantic layout rules: fan-outs for one-to-many, timelines for sequences, convergence for aggregation
- Export formats: `.excalidraw` (editable JSON), SVG, PNG
- Mermaid-to-Excalidraw bridge: `yannick-cw/mermaid-to-excalidraw-mcp` converts existing Mermaid diagrams into editable Excalidraw canvases

#### Productivity Impact for MeeSell (6.5/10)
Architecture diagrams — the K3s cluster topology, the module-federation shell + 6 remotes, the Celery worker pipeline, the auth OTP sequence — are genuinely useful for onboarding, stakeholder review, and sprint planning, and Excalidraw diagrams are editable rather than static PNGs. The auto-scan capability is directly relevant to the ongoing federation auth-singleton bug documentation in agent memory. However, this tool does not write code, run tests, or generate migrations. The MeeSell team's primary bottleneck is backend API development, database migrations, AI pipeline tuning, and micro-frontend federation — none of which are browser tasks.

#### Use Cases for MeeSell
- Auto-generate the MeeSell architecture diagram showing Angular 18 shell + 6 micro-frontend remotes + FastAPI + Celery workers + Valkey + PostgreSQL + GCS + Gemini 2.5 Flash — updatable every sprint
- Visualize the K3s cluster topology (dev/staging/prod namespaces, Traefik ingress, cert-manager, backup CronJob) from existing `k8s/` YAML files automatically
- Document the module-federation singleton sharing contract (`@mesell/core`, `@mesell/env`) as a component dependency diagram — directly relevant to the ongoing federation auth-singleton bug history
- Generate the Celery task pipeline diagram (image_tasks, generation_tasks) showing the Valkey broker/result-backend DB split
- Document the dual-identity auth flow (phone OTP + Google Sign-In) as a sequence diagram for onboarding new engineers

#### Limitations & Risks
- Does not write code, run migrations, or execute tests — purely a diagramming tool
- Diagram layout quality is inconsistent without the Playwright visual-validation pipeline; without it, overlapping text and misaligned arrows are common
- Silent failure gotcha: Claude Code requires `type: http` in `.mcp.json` for HTTP-based MCP servers; omitting it causes tools to not appear with no error message
- Community MCP servers (`yctimlin`, `whallysson`) have no built-in authentication or input validation
- PATH 2 skill approach requires Python + uv + Playwright — adds approximately 200MB toolchain to the dev machine
- No native CI/CD integration — diagrams are not automatically kept in sync with code changes unless Claude is re-prompted

#### Alternative
Mermaid (built into GitHub Markdown rendering, git-diffable, no extra tooling) is the best alternative for lightweight architecture documentation in PRs and wikis — Claude Code generates Mermaid natively without any plugin. For richer interactive diagrams, draw.io MCP (`jgraph/drawio-mcp`) is the alternative for Confluence or Visio export formats.

---

### 6. Agent Browser — 🟡 Moderate value

**What it is:** An open-source browser automation CLI for AI agents built by Vercel Labs (`vercel-labs/agent-browser`). It wraps a real Chromium browser via Chrome DevTools Protocol (CDP) — no Playwright or Puppeteer runtime required — and exposes high-level commands (navigate, snapshot accessibility tree, click, fill, screenshot, scrape, eval JS, network inspection) for AI agents to drive. Ships as both a Claude Code skill and an MCP stdio server.

**Official URL:** https://github.com/vercel-labs/agent-browser

**Integration:** `npm install -g agent-browser`, then `npx -y skills add vercel-labs/agent-browser --skill agent-browser --agent claude-code` to register the SKILL.md. Alternatively run `agent-browser mcp` to expose tools as an MCP stdio server.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | Apache 2.0 license; no subscription, no API key, no usage cap for the CLI/skill |
| Vercel Agent (separate cloud platform) | $0.30/run + LLM costs | Vercel's hosted Agent platform — not required for the CLI/skill to function |

#### Key Features
- Accessibility-tree snapshots: compact `@eN` element refs (~200-400 tokens per snapshot vs raw HTML) for token-efficient page understanding
- Navigation: URLs, multi-tab management, tab switching
- Interaction: click, fill forms, select, check, hover via `@eN` refs from the accessibility snapshot
- Screenshots: full-page or viewport; `--annotate` flag overlays numbered labels on interactive elements
- JavaScript eval: execute arbitrary JS in browser context
- Network tools: route inspection, request interception, HAR capture, custom headers, offline mode
- State management: cookies, localStorage, sessionStorage, saved auth sessions, browser profiles
- Background daemon: persists between commands so chained commands reuse the same browser session
- Tool profiles: `core` (default), `network`, `react`, `state`, `all` — selectable at startup
- Security controls: domain allowlist, action policy gating, action confirmation prompts

#### Productivity Impact for MeeSell (6.5/10)
The clearest win is automated E2E and QA testing: Claude can drive the Angular 18 PWA (catalog form, wizard, auth flows, price calculator) in a real browser from a single plain-English prompt, with no Playwright boilerplate to write or maintain. The network inspection tools can help debug federation manifest issues and auth token flows. However, the team's primary bottleneck is backend API development, database migrations, AI pipeline tuning, and micro-frontend federation — none of which are browser tasks. The main productivity uplift is in QA/verification workflows, saving perhaps 30-60% of QA time on UI regression.

#### Use Cases for MeeSell
- Automated E2E testing of the Angular 18 PWA: catalog creation wizard, SKU form, quality scorecard, price calculator, export page — driven by plain-English prompts instead of Playwright boilerplate
- Verifying federation auth singleton fix: Claude navigates shell → mfe-catalog → mfe-quality and confirms the user stays logged in across module nav (the exact bug logged in project memory)
- OTP login flow testing: Claude drives the onboarding component, fills phone number, submits, and verifies the JWT cookie is set correctly
- Visual regression checks: screenshot Angular pages before/after UI-DS changes and compare annotated snapshots
- Debugging federation manifest issues: navigate to each remote port (:4201-4222), snapshot the DOM, confirm correct build is being served

#### Limitations & Risks
- Not an Anthropic product — Vercel Labs is a third-party; no Anthropic SLA or support
- Community size is small — limited real-world bug reports, tutorials, and community troubleshooting compared to Playwright
- Background daemon can leave stale processes; requires `agent-browser doctor` to clean up
- Angular 18 accessibility tree may be partially incomplete for dynamically rendered Material components — snapshot quality depends on Angular's rendered DOM at snapshot time
- No built-in test reporting format — output is raw Claude text, not JUnit/TAP/Allure that CI dashboards consume natively
- Requires Chrome/Chromium installed or downloaded; adds approximately 150MB binary footprint

#### Alternative
Playwright MCP Server (`microsoft/playwright-mcp`) — free, open source, Microsoft-maintained, natively integrated with Claude Code as an MCP server, 23 core tools, zero extra install beyond npm, and benchmarks show comparable or better token efficiency for complex flows. Evaluate both before committing; Playwright MCP is more mature and Microsoft-backed.

---

### 7. Ralph Loop — 🟡 Moderate value

**What it is:** An official Anthropic-verified Claude Code plugin (184,000+ installs) that implements an iterative self-referential loop. It intercepts Claude Code session exit attempts via a Stop hook and automatically re-feeds the same prompt back to Claude, allowing iterative refinement across multiple passes until a configurable completion signal is detected or a maximum iteration count is reached.

**Official URL:** https://claude.com/plugins/ralph-loop

**Integration:** Install via the Anthropic plugin marketplace. Start a loop with `/ralph-loop "your task prompt here" --max-iterations 20 --completion-promise "ALL TESTS PASS"`. Cancel with `/cancel-ralph`.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | MIT/Apache licensed; no separate subscription; cost is purely Claude token consumption (~$10/hour of Claude compute per active loop per community estimates) |
| No paid tier | — | Use `--max-iterations` as a hard budget cap to prevent runaway costs |

#### Key Features
- Iterative Stop-hook loop: intercepts Claude session exit and re-injects the same prompt automatically
- `/ralph-loop` slash command with `--max-iterations` (safety ceiling) and `--completion-promise` (exact exit signal) flags
- `/cancel-ralph` command to terminate an active loop immediately
- State persistence in `.claude/ralph-loop.local.md` (YAML frontmatter: active, iteration, session_id, max_iterations, completion_promise)
- Completion detection via Perl multiline regex matching `<promise>` tags in last assistant output
- Preserves all file modifications and git history between iterations
- Compatible with Claude Code 2.1+ built-in equivalents (`/goal`, `/loop`, `/batch`) as alternatives
- Works across any language/stack

#### Productivity Impact for MeeSell (6.5/10)
Ralph Loop shines when tasks have objective, automated verification — pytest passing, Alembic migrations applying cleanly, ruff lint clearing, Angular `ng build` succeeding, or a specific API contract test going green. For those scenarios it can run overnight and compound iteration-over-iteration. However, MeeSell already has a sophisticated 19-agent Nexus/meesell-* dispatch architecture — Ralph Loop operates at a much lower abstraction level and does not understand the meesell-* agent boundaries, the two-step merge flow, or the HYBRID dispatch rule. Plugging it in naively at the project level would bypass the required coordinator merge-gate review. Its sweet spot is inside a specialist agent's worktree session for a tightly scoped, test-verified sub-task.

#### Use Cases for MeeSell
- Iterate inside a `meesell-database-builder` worktree until `alembic upgrade head` succeeds and all migration tests pass
- Run inside a `meesell-api-routes-builder` session until `pytest test_auth.py` and `pytest test_catalog.py` both exit 0
- Use within a `meesell-angular-component-builder` worktree to iterate until `ng build mfe-catalog --configuration production` exits cleanly
- Automate overnight ruff lint + mypy clean-pass loops on `backend/app/` after a large refactor
- Drive Celery task worker smoke tests in a loop until all image_tasks and generation_tasks complete without error
- Iterate Angular ESLint fixes on the federation shell until lint exits 0, avoiding manual back-and-forth

#### Limitations & Risks
- Requires objective, automatable completion signals — useless for tasks needing human judgment (UX decisions, API contract shape, component design)
- Exact string matching for completion detection is brittle — a prompt variation that never outputs the exact promise string loops forever until `max_iterations`
- No multi-agent awareness — does not understand meesell-* agent boundaries, coordinator→specialist hierarchy, or merge-gate review requirements; can silently bypass review gates if used carelessly
- Infinite loop / runaway cost risk if `--max-iterations` is not set — a single uncapped loop could exhaust an entire Pro monthly quota
- Loop state file (`.claude/ralph-loop.local.md`) is project-scoped — could conflict if multiple worktrees run Ralph loops simultaneously in the same repo
- Does not integrate with TICKETS.md, `.nexus/` state, or STATUS files — loop completion is invisible to the broader agent memory system
- Windows requires Git for Windows for the bash Stop hook; WSL can interfere

#### Alternative
Claude Code built-in `/goal` command (Claude Code 2.1+) is semantically equivalent to Ralph Loop but natively supported by Anthropic without an external plugin install, no Stop hook bash dependency, no state file management. For interval-based polling, the built-in `/loop` command or the project's own `/loop` skill covers the same ground.

---

### 8. Karpathy Skills — 🟡 Moderate value

**What it is:** A third-party, MIT-licensed behavioral guideline framework for Claude Code inspired by Andrej Karpathy's January 2026 X post cataloguing LLM coding failure modes. Ships as a CLAUDE.md file + Claude Code plugin (SKILL.md) encoding four rules: Think Before Coding, Simplicity First, Surgical Changes, and Goal-Driven Execution. Not an Anthropic product; maintained under the multica-ai GitHub org.

**Official URL:** https://github.com/multica-ai/andrej-karpathy-skills

**Integration:** Three paths. Path 1 (plugin): `/plugin marketplace add forrestchang/andrej-karpathy-skills` then `/plugin install andrej-karpathy-skills@karpathy-skills`. Path 2 (CLAUDE.md merge): `curl -o /tmp/karpathy.md` and manually merge. Path 3 (npx): `npx -y skills add forrestchang/andrej-karpathy-skills --skill karpathy-guidelines --agent claude-code`.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | MIT licensed; no tiers, no SaaS, no account required |
| No paid tier | — | Only cost is context tokens consumed when CLAUDE.md or SKILL.md is loaded |

#### Key Features
- Think Before Coding: Claude must state its interpretation, flag ambiguities, and ask before writing any code
- Simplicity First: no features beyond what was requested, no speculative abstractions, no unsolicited error handling
- Surgical Changes: modify only code directly satisfying the request; mention but do not fix unrelated issues; preserve existing style
- Goal-Driven Execution: convert vague tasks into verifiable success criteria and loop until criteria are demonstrably met
- Cross-project consistency via Claude Code plugin install (applies to all projects)
- Cursor IDE support via `.cursor/rules/karpathy-guidelines.mdc` adapter
- Multi-agent support: adapters for 40+ agents via `swarmclawai/andrej-karpathy-skills` npm package
- Intentionally brief — designed to merge cleanly with existing project CLAUDE.md files without conflict

#### Productivity Impact for MeeSell (6.5/10)
The four rules address genuinely universal pain points — Claude silently making wrong assumptions on ambiguous FastAPI route specs, over-abstracting service layers, or touching unrelated SQLAlchemy models during a surgical bug fix. "Think Before Coding" pays dividends on complex async SQLAlchemy + Pydantic v2 type gymnastics. "Surgical Changes" is directly relevant to a codebase with 19-agent dispatch where an agent touching the wrong service file is a real risk. However, MeeSell already has an extensive CLAUDE.md with project-specific conventions, agent routing rules, and architecture decisions that are more targeted than these generic principles. The biggest concrete win would be preventing drive-by rewrites during specialist builder dispatches.

#### Use Cases for MeeSell
- Preventing `meesell-database-builder` from refactoring existing Alembic migration files when only a new column is requested
- Stopping `meesell-angular-component-builder` from adding unsolicited RxJS operators or Angular Material imports to components that do not need them
- Forcing `meesell-services-builder` to surface ambiguity (e.g., "should enum validation use the public `/schema` or the internal cache?") before writing code — avoiding the `size_in_ltrs` 422 class of bugs
- Surgical Changes constraint during federation-related fixes to prevent accidental touching of shared `@mesell/core` singletons when only a remote component is in scope
- Merging into the existing MeeSell CLAUDE.md to give the Simplicity First rule to all 19 agents without a separate plugin install

#### Limitations & Risks
- CLAUDE.md instruction following is probabilistic, not deterministic — Claude can still ignore, misunderstand, or over-apply the rules under ambiguous prompts or long context windows
- No enforcement mechanism: these are behavioral prompts, not code-level constraints or linters
- Community-identified gap: rules are silent on session/token budget boundaries — without a cap, a Goal-Driven loop can run 90+ minutes; recommended mitigation is adding a ~4,000 token per-task budget rule manually
- Must be carefully merged into the existing CLAUDE.md — blind overwrite will destroy MeeSell's extensive project-specific conventions
- Canonical repo moved from `forrestchang/` to `multica-ai/` — old links 301-redirect but documentation in the wild may point to the wrong source
- The plugin marketplace install path was noted as "not locally proven" by at least one reviewer — the direct CLAUDE.md merge or npx path is more reliable

#### Alternative
For MeeSell's structured multi-agent context, a more targeted alternative is to write bespoke CLAUDE.md guard rails per agent role (already partially done via `.claude/agents/meesell-*.md` specs) rather than a generic cross-cutting guideline. The newton-skill (PBNZ/newton-skill) adds adversarial reasoning on top of the Karpathy baseline — useful for `meesell-services-builder` when it needs to challenge ambiguous specs.

---

### 9. MCP Builder — 🟡 Moderate value

**What it is:** A family of Claude Code skills/plugins that guide developers through designing, scaffolding, and publishing Model Context Protocol (MCP) servers. The official Anthropic plugin `mcp-server-dev` (24,500+ installs, Anthropic Verified) is the most complete and authoritative version; community variants `mcp-builder` and `fastmcp-builder` also exist. All are SKILL.md-based slash-command plugins — not standalone npm packages or MCP servers themselves.

**Official URL:** https://claude.com/plugins/mcp-server-dev

**Integration:** `/plugin install mcp-server-dev@claude-plugins-official` for the official variant. Community `fastmcp-builder` (Python-focused): clone `husniadil/fastmcp-builder`, add SKILL.md to `.claude/skills/`.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | All variants free and open-source (MIT); included with Claude Code subscription at no extra cost |
| No paid tier | — | No per-skill or per-server fee |

#### Key Features
- 5-phase guided MCP server design workflow: use-case interrogation → deployment model selection → tool-design pattern → framework selection → scaffolding
- 4 deployment path recommendations: Remote streamable-HTTP (default for cloud APIs), MCPB (local bundled), local stdio (prototype only), MCP App (with in-chat UI widgets)
- Two tool-design patterns: one-tool-per-action (≤15 operations) or search+execute (large API surfaces)
- Auth support: API keys, OAuth 2.0 with CIMD/DCR patterns, plus security hardening guidelines
- Interactive MCP App support: form widgets, searchable pickers, confirmation dialogs, charts
- MCPB packaging: bundles local stdio servers with Node/Python runtime
- Framework selection guidance: TypeScript MCP SDK vs FastMCP (Python)
- `fastmcp-builder` variant: 145-test reference project, OAuth integration, dual-mode auth/local testing, Pydantic v2 models

#### Productivity Impact for MeeSell (6.5/10)
For MeeSell specifically, MCP Builder becomes genuinely high-value the moment the team decides to expose FastAPI services, PostgreSQL state, or K3s infrastructure as MCP servers for the meesell-* agent fleet to consume directly from within Claude sessions. The Python/FastMCP pathway is a direct fit for the stack. However, for standard sprint-by-sprint feature development (Angular components, backend routes, Alembic migrations, Celery tasks), this skill adds zero daily productivity. Its value is conditional and one-time rather than recurring.

#### Use Cases for MeeSell
- Build a `mesell-internal-mcp` MCP server wrapping FastAPI endpoints so Claude Code agents can call live staging/prod APIs directly from within sessions without copy-pasting curl commands
- Wrap PostgreSQL queries (catalog status, SKU counts, quality scores) as MCP resources so Claude Code can fetch live DB state during debugging sessions
- Create a GCS MCP server exposing image upload/download tools tailored to MeeSell's bucket layout — useful for `meesell-image-precheck-builder` agent testing
- Build a Celery task MCP server so Claude Code can trigger background jobs (image processing, export generation) and poll status from within a session
- Create a K3s/kubectl MCP server tailored to the dev/staging/prod namespaces for `meesell-infra-builder` to use without leaving Claude Code

#### Limitations & Risks
- Guided methodology skill, not an autonomous code generator — Claude still asks many clarifying questions; it does not fully auto-generate a working MCP server
- Elicitation (mid-tool user input) requires Claude Code version ≥2.1.76; Claude Desktop support unconfirmed
- Local stdio deployment is explicitly not recommended for distribution — personal prototypes only
- `fastmcp-builder` is Python/FastMCP only — not suitable if your MCP server needs to be TypeScript/Node.js
- Cannot introspect existing FastAPI routes autonomously to auto-generate MCP tool stubs; developer must describe the API surface manually
- Three different "MCP Builder" variants exist with no clear single canonical home — community confusion between variants is real

#### Alternative
For teams who want to consume existing MCP servers rather than build custom ones: use `claude mcp add` with pre-built community servers (postgres MCP, GCS MCP, kubectl MCP). For a Python MCP server from scratch without a guided skill: use the FastMCP Python library directly (`pip install fastmcp`) — its documentation is comprehensive without needing the builder skill.

---

### 10. Frontend Designer — 🟡 Moderate value

**What it is:** An official Anthropic Claude Code plugin (829,316 installs) authored by Anthropic engineers that instructs Claude to commit to a distinctive, intentional aesthetic direction — palette, typography, layout, motion — before writing a single line of frontend code, and to self-critique the plan against generic AI defaults before building. It is a ~400-token SKILL.md file, not a UI component library or MCP server.

**Official URL:** https://claude.com/plugins/frontend-design

**Integration:** `/plugin install frontend-design@claude-plugins-official`. Once installed, Claude automatically loads the context when asked for any frontend UI work. Can also be invoked explicitly as `/frontend-design:frontend-design`.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | Open-source SKILL.md in the public anthropics/claude-code repo; no separate paid tier |
| No paid tier | — | Cost is ~400 tokens of skill context per invocation (negligible) |

#### Key Features
- Aesthetic direction framework: forces Claude to define palette (4-6 named hex values), type roles (display/body/utility faces), layout concept, and a single "signature element" before writing any code
- Anti-generic-AI-slop enforcement: explicitly bans Inter+purple-gradient+rounded-cards defaults, cream+serif+terracotta, near-black+acid-green unless brief specifically requires them
- Two-pass brainstorm-then-build process: plan phase produces a compact token system; critique phase checks plan against generic defaults before code is written
- Typography discipline: requires pairing display and body faces deliberately with intentional weights
- Motion design guidance: deliberate animation strategy — page-load sequences, scroll-triggered reveals, hover micro-interactions
- Writing-as-design principles: active voice, consistent action vocabulary, directional error messages
- Quality floor: responsive down to mobile, visible keyboard focus, reduced-motion CSS respected
- Framework-agnostic: works with Angular, React, Vue, Svelte, vanilla HTML/CSS
- Chainable with `/baseline-ui` and `/fixing-accessibility` for a three-skill pipeline

#### Productivity Impact for MeeSell (5.5/10)
The plugin has genuine value for new page conception and marketing/landing work where Angular constraints are loose. However, it is entirely aesthetic/design-philosophy guidance with zero Angular-specific knowledge — no standalone components, no signals, no OnPush, no Angular Material theming awareness. The MeeSell CLAUDE.md already enforces Angular 18 patterns far more precisely. MeeSell already uses Tailwind + Angular Material with a locked design direction post PR #327, so the plugin's anti-generic defaults are less useful when an established UI-DS is already in place. Community reviewers note that updating existing components leads to full regeneration rather than incremental changes.

#### Use Cases for MeeSell
- New onboarding flow pages (phone OTP screen, Google Sign-In screen) — get a distinctive first-impression design before locking to Angular templates
- Landing/marketing page for MeeSell (outside the Angular app) — strongest use case, no framework constraint
- Initial dashboard shell wireframe ideation before `meesell-angular-component-builder` codes it
- Error state and empty state copy + visual treatment — the "writing as design" principles directly improve these
- Catalog preview page aesthetic direction — pushes beyond generic card grids

#### Limitations & Risks
- Framework-agnostic means zero Angular 18 awareness: no standalone components, no signals, no OnPush, no Angular Material integration guidance — outputs generic HTML/CSS that must be translated to Angular templates
- Aesthetic bias conflicts with established design systems: once a UI-DS is locked (as MeeSell's is post PR #327), the plugin's drive for distinctive choices can work against consistency
- Community-confirmed issue: asking to tweak an existing component triggers a full design re-pass instead of targeted edits — wasteful on token budget
- No component-library awareness: does not know about Angular Material theme, PrimeNG icon set, or Tailwind config — may generate arbitrary CSS instead of utility classes
- Auto-activation means it fires on all frontend tasks including surgical Angular fixes where design planning is unwanted overhead

#### Alternative
For Angular 18 + Tailwind + Material stacks, stronger investments are: (1) the Angular Expert Claude skill in the same plugin ecosystem for Angular-specific patterns; (2) Context7 MCP server for live Angular/Material documentation lookup; (3) a curated CLAUDE.md design section documenting the project's own design tokens, Material theme config, and Tailwind palette — zero token overhead and zero security risk.

---

### 11. UI UX Pro Max — 🔴 Low value

**What it is:** A third-party, MIT-licensed Claude Code skill that injects a searchable database of 67 UI styles, 161 color palettes, 57 font pairings, 99 UX guidelines, 25 chart types, and 161 industry-specific reasoning rules into Claude sessions. When activated it runs a 4-step workflow using a local Python BM25 search engine over CSV data files.

**Official URL:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

**Integration:** Install as a Claude Code plugin. Requires Python 3.x installed and accessible in the project environment for the search CLI to function.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| Free | $0 | MIT licensed; no paid tier; all design data, CLI, and skill definition free |
| No paid tier | — | No SaaS subscription, no API key required |

#### Key Features
- 67 UI styles (glassmorphism, claymorphism, brutalism, bento grid, minimalism, dark mode, and others)
- 161 color palettes organised by product category
- 57 Google Font pairings with personality matching
- 25 chart types for dashboards and data visualisation
- 99 UX guidelines covering accessibility, touch targets, forms, navigation, animation, responsive breakpoints
- 161 product-type reasoning rules for auto-generating industry-specific design systems
- BM25 search engine over 344+ CSV design resources across 10 domains and 16 tech stacks
- Stack-specific implementation guidance for React, Next.js, Vue, Svelte, Tailwind, shadcn/ui, SwiftUI, Flutter, React Native, Jetpack Compose, Astro, Angular, Nuxt.js, Laravel, HTML+CSS
- Accessibility auditing: contrast ratios, focus states, ARIA labels, touch target sizes

#### Productivity Impact for MeeSell (4.5/10)
Angular is NOT a primary supported stack in the skill's core design CSV data and reasoning rules — which are optimised for React/Next.js/Vue/Svelte. The skill provides zero Angular Material-specific guidance (no component theming, no CDK, no `mat-*` selectors). The backend (FastAPI/Python) and infra (K3s/GCP/PostgreSQL/Gemini) are explicitly out of scope. The UX guidelines and color palette/typography recommendations are framework-agnostic and are the only genuinely applicable output. For a React SaaS team this would score 7-8; for Angular 18 + Material it is materially less useful.

#### Use Cases for MeeSell
- Generating initial color palette and typography system for the Angular PWA (framework-agnostic output is usable)
- WCAG accessibility audit prompts for Angular Material components (contrast ratios, focus rings, ARIA)
- Chart type selection for the pricing P&L breakdown and quality scorecard components
- Responsive breakpoint and touch-target validation for Ionic/Capacitor Phase 2 mobile wrap

#### Limitations & Risks
- **CRITICAL SECURITY ISSUE (unfixed as of research date):** CVE-level code injection vulnerability in `tailwind_config_gen.py` (Issue #246, CVSS 9.3 Critical) — the `_format_plugins()` method interpolates plugin names into `require()` statements without sanitisation, enabling RCE when generated `tailwind.config.js` is loaded by Node.js. PR #275 was opened but not yet merged by maintainers. **This alone is sufficient grounds to avoid installing in any production development environment.**
- Angular 18 + Angular Material is NOT a primary supported stack — skill data and reasoning rules are optimised for React/Next.js/Vue/shadcn/ui
- Skill activates automatically on any UI-related prompt — can conflict with MeeSell's strict meesell-* agent routing rules in CLAUDE.md
- Adds approximately 11k tokens to every triggered Claude session — RAM/cost consideration on the 8GB dev machine
- Star count inflation risk: third-party aggregator sites report wildly inconsistent numbers — genuine adoption is hard to verify
- Community sentiment is sparse: no substantial Reddit/HN discussion found; independent critical reviews absent

#### Alternative
For Angular 18 + Tailwind + Material design guidance: (1) a curated CLAUDE.md design section documenting the project's own design tokens, Material theme config, and Tailwind palette — zero token overhead and zero security risk; (2) the official Angular Material Tailwind schematic (`npm package @angular/material`) for generating a Material Design theme; (3) Figma MCP server (official, from Figma) for stack-agnostic design spec access.

---

### 12. HyperFrameworks — ⛔ Skip

**What it is:** This product does not exist. Exhaustive searches across GitHub, npm, Reddit, Claude Directory, and broader web sources returned zero results for any product named "HyperFrameworks" as a Claude Code skill, MCP server, npm package, or any other integration format. The name does not appear in any Claude Code skill registry, Anthropic documentation, MCP server directory, or community listing as of June 2026.

**Official URL:** Not found — no product exists at this name.

**Integration:** Not applicable.

#### Pricing
| Tier | Cost | What You Get |
|------|------|-------------|
| N/A | N/A | Product does not exist; no pricing to report |

#### Key Features
- Product does not exist — no features to list
- Possible confusion with HyperFrames (HeyGen): an HTML-to-MP4 video rendering framework for AI agents — entirely unrelated to SaaS code generation or framework scaffolding
- Possible confusion with generic Claude Code plugin collections that use "framework" in their branding (SuperClaude_Framework, claude-forge)

#### Productivity Impact for MeeSell (0/10)
A product that does not exist cannot deliver productivity value. No score is meaningful.

#### Use Cases for MeeSell
- None — the product does not exist.

#### Limitations & Risks
- Any claims about this product's features, pricing, or capabilities would be hallucinated
- The related product HyperFrames (HeyGen) is a video rendering tool with no relevance to FastAPI + Angular 18 SaaS development

#### Alternative
For Claude Code productivity on a FastAPI + Angular 18 SaaS stack, evaluate these real tools instead: (1) SuperClaude_Framework (`github.com/SuperClaude-Org/SuperClaude_Framework`) — configuration framework with specialized commands and cognitive personas; (2) `claude-forge` (`github.com/sangrokjung/claude-forge`) — 11 AI agents, 36 commands, 15 skills, oh-my-zsh-style plugin framework; (3) `levnikolaevich/claude-code-skills` — plugin suite covering Agile pipeline, project bootstrap, documentation generation, and codebase audits.

---

## Recommended Action Plan

### Immediate (this week)

- **Install Skill Creator** (`/plugin install skill-creator@claude-plugins-official`) and invest 2-3 hours authoring 5 project-specific skills: FastAPI router conventions, Angular standalone component patterns, Alembic migration rules, K3s deployment checklist, and the Gemini prompt budget skill. This compounds on every future agent dispatch and is the single highest-ROI action available.
- **Get legal sign-off on AGPL-3.0 for claude-mem**, then install on the founder's primary machine only with `npx claude-mem install`; keep Endless Mode off; treat it as a supplement to (not replacement for) the existing `.claude/agent-memory/` system.
- **Install Context7 on the Pro plan** (`npx ctx7 setup --claude`) at $10/seat/month — the Pydantic v2, SQLAlchemy 2.0 async, and Angular 18 signals docs are the immediate payback. Verify that FastAPI, Alembic, and Angular Material 18 all have good coverage in the registry before committing to the subscription.
- **Cherry-pick merge the Surgical Changes and Think Before Coding sections from Karpathy Skills into the existing MeeSell CLAUDE.md** (do NOT install as a plugin globally; use the direct CLAUDE.md merge path from `multica-ai/andrej-karpathy-skills`). Skip the Goal-Driven Execution rule — Nexus already handles this.
- **Install Frontend Designer** (`/plugin install frontend-design@claude-plugins-official`) — zero cost, one command, and add a CLAUDE.md gate scoping it to new-page and marketing contexts only, not Angular component surgery.

### Short-term (next month)

- **Evaluate claude-mem Endless Mode** only after the stability issues (SQLite locks, macOS crashes) are confirmed resolved in a new release — the 60-90s per-tool latency is currently unacceptable for builder-agent sessions.
- **Install the official Excalidraw MCP** (PATH 1 via Claude.ai Connectors, `type: http` in `.mcp.json`) to auto-generate the module-federation component map and K3s cluster diagram from existing code/YAML — directly relevant to the ongoing federation auth-singleton bug documentation. Do not install PATH 2 (Playwright toolchain) until the team reaches a size where architecture docs block velocity.
- **Pilot Ralph Loop inside one specialist worktree** (`meesell-services-builder` or `meesell-database-builder`) for a tightly scoped sub-task with a clear automated exit signal (e.g., `pytest test_quality.py` exits 0). If the pilot works cleanly, expand to other builder agents. Always use `--max-iterations` as a hard budget cap and never use Ralph Loop at the project level where it could bypass the coordinator merge-gate review.
- **Build 2-3 internal MCP servers using `mcp-server-dev`**: start with a PostgreSQL MCP server exposing catalog/SKU/quality state for live debugging sessions, then a GCS MCP server for image precheck testing. Use the `fastmcp-builder` Python reference project as the starting template. This one-time investment compounds across all future agent sessions.
- **Install Agent Browser** (`agent-browser install`) once the Angular 18 UI stabilises post-federation fixes and QA automation on PRs becomes a priority. Evaluate alongside Playwright MCP before committing.

### Defer / Evaluate Later

- **SuperPowers** — install globally once the next major feature track begins, but configure CLAUDE.md to suppress brainstorm/plan skills when running a full Nexus dispatch to avoid double-ceremony. Use selectively for debugging (four-phase methodology) and TDD enforcement on backend builders.
- **Karpathy Skills Goal-Driven Execution rule** — deferred because the Nexus SDLC already handles this via staged dispatch and SDLC gates. Revisit if the team grows beyond the current founder-directed model and needs more self-directed agent behavior.
- **Context7 Upgrade to Enterprise** — relevant only if private repository parsing for internal MeeSell FastAPI/Angular documentation becomes a need. Not required at current scale.
- **Excalidraw PATH 2** (coleam00 skill with Playwright visual validation) — best investment once the team reaches a size where architecture docs block onboarding or external stakeholder reviews, or when an external audit is incoming.

### Skip

- **HyperFrameworks** — does not exist. Do not install, do not act on any third-party claims about its features. Research SuperClaude_Framework or claude-forge as real alternatives for framework scaffolding.
- **UI UX Pro Max** — do not install in any production development environment until the CVSS 9.3 RCE vulnerability in `tailwind_config_gen.py` (Issue #246) is confirmed patched and merged. Beyond the security issue, the skill's primary value is for React/Next.js/Vue stacks — MeeSell uses Angular 18 + Angular Material where the skill has no idiomatic knowledge and the risk-to-value ratio does not justify installation.

---

## Free-Tier Summary

All skills researched (except Context7 for team use) have genuinely free tiers adequate for evaluation. Key notes on practical free-tier limits:

| Skill | Free Tier Quality | Practical Limit for MeeSell |
|-------|-------------------|----------------------------|
| Skill Creator | Excellent — fully bundled with Claude Code | None beyond token usage |
| claude-mem | Excellent — fully free, all features | AGPL-3.0 legal review needed for commercial SaaS |
| SuperPowers | Excellent — MIT, no caps | Token overhead on 8GB RAM machine |
| Excalidraw | Excellent — official MCP is free | Excalidraw+ ($7/month) optional for cloud collab |
| Agent Browser | Excellent — Apache 2.0, no caps | LLM tokens per browser interaction billed by Anthropic |
| Ralph Loop | Excellent — free plugin; runaway cost risk | Always set `--max-iterations`; ~$10/hour of compute per loop |
| Karpathy Skills | Excellent — MIT, no caps | None; trivial token overhead |
| MCP Builder | Excellent — MIT, no caps | None beyond token usage during guided sessions |
| Frontend Designer | Excellent — official Anthropic, ~400 tokens/invocation | None |
| Context7 | Inadequate for a team — 1,000 calls/month (83-92% cut Jan 2026) | Pro plan at $10/seat/month required for active development |
| UI UX Pro Max | Free but blocked by unpatched CVSS 9.3 RCE | Do not install until security fix confirmed |
| HyperFrameworks | N/A — product does not exist | N/A |

---
*Report generated by Nexus Intelligence Layer — MeeSell AI SDLC*