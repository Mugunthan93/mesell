# MeeSell — Master Session Dispatch Documentation

> Self-contained kickoff package for the next MeeSell master session.
> **Founder fills in:** the session NAME and the MODEL (placeholders below).
> **Predecessor:** `meesell-master-session-5` (closed 2026-06-20).
> Further task instructions will be appended by the founder under §7.

---

## 0. Session Header — FOUNDER TO SET

| Field | Value |
|---|---|
| **Session Name** | `__________________________` ← (founder names this, e.g. `meesell-master-session-6`) |
| **Model** | `__________________________` ← (founder sets, e.g. Opus / Sonnet) |
| Role | Director (master orchestration session) |
| Predecessor | `meesell-master-session-5` |
| Repo / branch | `/Users/mugunthansrinivasan/Project/mesell` @ `develop` |
| develop HEAD at handoff | `68568b7` |
| Date opened | `__________` |

---

## 1. KICKOFF PROMPT  *(paste this as the first message to start the session)*

```
You are the MeeSell master Director session "<SESSION_NAME>".

Before doing anything, run the BOOT SEQUENCE in
docs/sessions/MASTER_SESSION_DISPATCH.md §2, then give me the boot briefing
(under 200 words) and WAIT for my instructions.

Operate under the MeeSell rules in CLAUDE.md: only meesell-* agents do MeeSell
work; the HYBRID dispatch rule (coordinator SPEC → specialist BUILD → coordinator
MERGE-GATE for code; single-agent fast mode for docs/chores); founder merges all
develop PRs; never git in the master tree (use worktrees); password login only,
READ-ONLY scraping / never go-live; never commit or echo credentials.

Read the carry-forward state in §3–§6 of that file and the master-session memory
at .claude/projects/-Users-mugunthansrinivasan-Project-mesell/memory/MEMORY.md
(start with master-session-5-handoff.md). Do not start any work until I tell you
what to do — my instructions will be under §7.
```

---

## 2. BOOT SEQUENCE  *(the session runs these on start, before acting)*

1. **Read memory (highest signal first):**
   - `.claude/projects/-Users-mugunthansrinivasan-Project-mesell/memory/MEMORY.md` → then `master-session-5-handoff.md`.
   - `.claude/agent-memory/nexus-level-0-director/MEMORY.md` (Director memory).
   - This file (§3–§6).
2. **Verify repo state (read-only):**
   - `git -C /Users/mugunthansrinivasan/Project/mesell log origin/develop --oneline -5`
   - `git worktree list` (expect: master + `gauth-live` only)
   - `gh pr list --state open` (expect: 0 at handoff)
3. **Verify the local dev stack health:**
   - `curl -s -o /dev/null -w "%{http_code}" http://localhost:4200` → 200 (shell)
   - `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` → 200 (backend)
   - Remotes on :4201–:4206 (static serve.js). Calculator: `http://localhost:4200/catalogs/<id>/pricing`.
   - If the stack is down, do NOT auto-rebuild — report it and ask (rebuilds are memory-heavy; see §4 RAM note).
4. **Check machine memory** (the binding constraint): `vm_stat` free pages + `sysctl vm.swapusage`. If swap is near full / free RAM < ~150 MB, flag it in the briefing before any build.
5. **Produce the boot briefing** (≤200 words): where we are (1 sentence) · what changed since session-5 (1–3 items, highest signal) · what you recommend next / what you're ready for. Then **WAIT** for founder input — never proceed unprompted.

---

## 3. CONSOLIDATED STATE  *(as of 2026-06-20, develop @ `68568b7`)*

### Shipped & merged
- **Price Calculator rework W1–W6 COMPLETE & LIVE** — confirmed Meesho settlement model (commission 0% everywhere; shipping = per-category constant, weight-independent; seller bears only 18% GST on shipping). Calculator at `:4200/catalogs/<id>/pricing`, computes OFFLINE from `backend/app/data/meesho_pricing_lookup.json` (3,772 cats). Golden proof ₹61.78. PRs #305 (BE), #306 (FE), #316 (apply-price/export), #313 (docs), #321 (W6 monthly refresh, STAGE-ONLY).
- **Federation auth-singleton logout FIXED** (#328) — `@mesell/*` libs pinned `version:'1.0.0' + singleton + strictVersion` across all 7 federation configs + 4 lib package.json. Browser-confirmed: shell→remote nav keeps session. (NF 3.5.5 hardcodes `strictVersion:false` for tsconfig-alias libs → dedup keys on packageName+version+singleton, all now consistent.)
- **UI Design-System decoupling COMPLETE/sealed** — phases 0–7 (#256–#276); all 5 contracts strict + FE Gate required; theme/icon one-file swap proven. Last spec doc landed (#327).
- Other merged this period: #307 dev-DB backup · #314 pricing artifacts · #318 browse RemoteFailure fix · #319 auth-refresh-storm fix · #320 icon registry · #322 /auth/me phone-nullable · #323 Razorpay Subs Waves 1–5 · #325 Razorpay dev-mock · #326 mfe-billing CI.

### Repo / worktrees (fully pruned)
- Worktrees: **master (develop)** + **`gauth-live`** (KEEP per founder ruling) only. Everything else cleaned.
- 0 open PRs.

### Local stack
- Static `serve.js` builds on :4200–:4206 + uvicorn `--reload` on :8000. All @mesell/core = 1.0.0. Stack green at handoff.

---

## 4. OUTSTANDING / CARRY-FORWARD

| # | Item | Owner | Notes |
|---|---|---|---|
| 1 | **Rotate `.meesho_creds.env`** before first LIVE pricing census | Founder | Exposed in earlier chats. NO live census has run; W6 monthly job is built+tested only; NO launchd schedule installed (manual/supervised by design). |
| 2 | **8 GB RAM / swap pressure** | Founder | Build deadlocks are a memory symptom. Levers: close idle Claude sessions (~7 ≈ 1.4 GB), reboot to reset swap. Builds MUST be one-at-a-time, direct `ng` binary (NOT npx), kill esbuild between. |
| 3 | **Google auth HELD** | Founder | Verified working on isolated :4210 stack but blocked on Decision #5 amendment ratification. `feature/google-auth` + `gauth-live` worktree = KEEP. |
| 4 | **Pre-existing debt** (not blocking) | Backend | `ng test` red on unbuilt `@mesell/core` ApiClient/NetworkService (Wave-6 service-layer gap); separate from scanner-based FE Gate. |
| 5 | Optional UI-DS ergonomics | FE | Opportunistic adoption of grouped `MEE_*` aggregators; regression-proof already — never a big-bang. |

---

## 5. STANDING CONSTRAINTS  *(carried — non-negotiable)*

- **Canonical git workflow: `docs/GIT_WORKFLOW.md`** is the single source of truth for branching, worktree, and merge rules. The constraints below are the carry-forward subset — if anything conflicts, `docs/GIT_WORKFLOW.md` wins.
- **Only `meesell-*` agents** do MeeSell work. Never `nexus:*`, `general-purpose`, `Explore`, `Plan`.
- **Two-step merge flow** (per `docs/GIT_WORKFLOW.md`): `feature/{slug}/{group}` --squash--> `feature/{slug}/integration` (Director/coordinator merges) --merge-commit--> `develop` (**founder** merges) → staging → main (tagged). The legacy `ticket/{number}-desc` + single-step "squash merge to main" flow is RETIRED.
- **Founder merges all develop PRs** (the `integration → develop` step). Director opens PRs, never merges them unless told.
- **Never git in the master tree** — every feature-group works in its own worktree off develop. `MESELL_ALLOW_MASTER_GIT=1` is the deliberate-recovery override for safe ops only (branch -D, worktree prune).
- **Password login only / NO OTP.** **READ-ONLY scraping, never go-live.** Never commit/echo credentials.
- **DB tests** use a disposable `TEST_DATABASE_URL`, NEVER the live dev DB (prior incident drop_all'd it; recovery = `make seed`).
- **Never amend LOCKED docs** (`V1_FEATURE_SPEC.md`, `PRICING_LOCKED.md`, `INFRASTRUCTURE_PLAYBOOK.md`, `LEGAL_AND_COMPLIANCE_INFO.md`) without founder approval.
- Dev-only / zero-spend posture unless told otherwise.

---

## 6. AGENT FLEET + DISPATCH RULES

> **Branching / worktree / merge convention: see `docs/GIT_WORKFLOW.md`** (canonical). Each dispatched feature-group works on its own `feature/{slug}/{group}` branch in its own worktree + localhost env; group→integration is squash-merged by the Director/coordinator, integration→develop is merge-committed by the founder.

**HYBRID dispatch (founder-ruled):**
- **Code-heavy** (feature code, backend/auth, AI pipeline, federation config): THREE steps — (1) coordinator produces SPEC, (2) session dispatches the named SPECIALIST to build, (3) coordinator runs the MERGE-GATE review (a real gate — can reject). Then open PR for founder merge.
- **Docs / status / chores:** single-agent fast mode (coordinator/lead executes directly).
- Coordinators have NO Agent tool — the master session runs the hierarchy for them.

**Roster:** `meesell-section-coordinator` (Tier-1) · `meesell-infra-builder` (ops/cleanup) · `meesell-backend-coordinator` → database/api-routes/services/auth builders · `meesell-frontend-coordinator` → angular component/service/ui-styler builders · `meesell-ai-coordinator` → prompt-engineer/category-picker/image-precheck · `meesell-data-engineer` → xlsx-parser/scraper-maintainer · `meesell-legal-writer`. Full specs: `docs/MEESELL_AGENT_REGISTRY.md`.

**Dev/build gotchas:** lean sequential builds only (memory); static serve.js not `ng serve`; after FE/BE changes land on develop, rebuild the relevant remote(s) from develop + restart serve.js + hard-refresh :4200; backend `--reload` restart for BE changes.

---

## 7. FURTHER INSTRUCTIONS  *(founder appends below — the actual work for this session)*

> _(empty — founder will fill this in)_
