# MeeSell Testing Agent & Skills Design

**Date:** 2026-06-22
**Status:** Approved — pending implementation
**Author:** Director (master session)
**Implements:** QA pillar for the MeeSell 19-agent fleet

---

## 1. Problem Statement

The MeeSell 19-agent fleet builds code but has no agent whose job is to write tests.
Three compounding gaps exist:

1. **Coverage gaps** — whole feature areas (routes, services, Angular pages) ship with
   no tests, or tests written ad-hoc by builders with no consistency.
2. **No test author in the fleet** — the coordinator → merge-gate-review loop does not
   catch absent tests because there is no agent producing them.
3. **No E2E / browser-level testing** — unit and integration tests exist across
   `backend/tests/`, but no Playwright suite exercises the full seller journey through
   the shell + 6-remote module-federation stack.

The `meesell-test-writer` agent was explicitly deferred to V1.5 in CLAUDE.md. This spec
supersedes that deferral and delivers a full QA pillar.

---

## 2. Approach Selected

**Full QA Wave Model** — a self-contained fourth coordinator pillar alongside
backend / frontend / ai. A `meesell-qa-coordinator` owns the strategy and dispatches
three specialists. The wave runs as a dedicated sprint after feature waves complete —
it does not block individual feature PRs.

Two alternatives were considered and rejected:

- **Thin start (one agent + one skill):** Produces shallow, inconsistent test quality
  across Python, Angular, and Playwright simultaneously.
- **Bolt-on to existing coordinators:** No agent has a cross-domain view; gaps at
  module boundaries go undetected.

---

## 3. Fleet Architecture

The fleet grows from **19 → 23 agents**.

```
master session
  ├── meesell-backend-coordinator   (existing)
  ├── meesell-frontend-coordinator  (existing)
  ├── meesell-ai-coordinator        (existing)
  └── meesell-qa-coordinator        (NEW — peer, not subordinate)
        ├── meesell-backend-test-writer
        ├── meesell-frontend-test-writer
        └── meesell-e2e-test-writer
```

### 3.1 New Agents

| Agent | Model | Tier | Owns |
|---|---|---|---|
| `meesell-qa-coordinator` | Opus | Coordinator | Test specs, `docs/status/feature_board_qa.md`, merge-gate review of all test PRs |
| `meesell-backend-test-writer` | Sonnet | Specialist | pytest unit + integration + eval + module tests |
| `meesell-frontend-test-writer` | Sonnet | Specialist | Angular Karma/Jasmine component specs + service tests |
| `meesell-e2e-test-writer` | Opus | Specialist | Playwright end-to-end critical seller flows |

`meesell-e2e-test-writer` is Opus (not Sonnet) because navigating the shell + 6-remote
module-federation topology, auth-cookie flows, and Playwright page-object design
requires high-reasoning capacity — same justification as `meesell-services-builder`
and `meesell-auth-builder`.

### 3.2 HYBRID Dispatch Rule (unchanged)

The existing HYBRID dispatch rule applies to the QA pillar without modification:

- **Code-heavy construction** (writing test files): THREE-step — (1) QA coordinator
  produces test spec, (2) master session dispatches specialist with spec, (3) QA
  coordinator runs merge-gate review.
- **Docs / status flips / chores**: single-agent fast mode — coordinator executes
  directly.

---

## 4. QA Wave Integration

### 4.1 Trigger

The QA wave is **explicitly dispatched** by the master session after a batch of
features have merged to `develop`. It is not automatic.

```
Founder merges feature/section-N/integration → develop
  → Master session dispatches meesell-qa-coordinator
     "Run QA Wave 1 against: auth-otp, xlsx-export, catalog-wizard"
```

### 4.2 Branch Strategy

```
feature/qa-wave-N/backend    ──squash──┐
feature/qa-wave-N/frontend   ──squash──┼──► feature/qa-wave-N/integration ──merge──► develop
feature/qa-wave-N/e2e        ──squash──┘
```

Each specialist works in its own worktree. No shared state between branches mid-wave.

### 4.3 Inputs to the QA Coordinator

When dispatched, the master session passes:

| Input | Source |
|---|---|
| Feature slugs to cover | Master session (explicit list) |
| `docs/V1_FEATURE_SPEC.md` | Locked spec — what was promised |
| `docs/status/feature_board_qa.md` | What is already tested (coordinator maintains this) |
| `backend/tests/` structure | Read by coordinator to identify gaps |
| `frontend/src/` + `frontend/libs/` | Read to identify components with no `.spec.ts` |

### 4.4 QA Coordinator Output — Test Spec (per specialist)

Each test spec contains:

1. **Coverage map** — which files/routes/components are untested
2. **Test case list** — explicit list of what to write (not "write tests for auth" but
   "write test: OTP bypass `000000` accepted in dev, rejected in prod")
3. **File targets** — exact paths for new test files
4. **Coverage target** — measurable exit criterion (e.g. "all 7 IAM routes have at
   least one happy-path + one error-path test")

### 4.5 Merge-Gate Review Checklist

The QA coordinator checks each specialist PR for:

- [ ] Tests actually run (`pytest` / `ng test` output in PR description)
- [ ] `TEST_DATABASE_URL` safety guard not bypassed
- [ ] No real external calls (Gemini, MSG91, Razorpay, GCS all mocked at boundary)
- [ ] Coverage target from the test spec is met
- [ ] No test that only passes because it asserts nothing

---

## 5. The 3 Skills

Each skill encodes both **Conventions** (how to write tests the MeeSell way) and
**Taxonomy** (explicit list of what must be covered per domain).

### 5.1 `meesell-backend-testing`

**Trigger:** Any time pytest tests are being written for the MeeSell backend.

#### Conventions

- Always use `TEST_DATABASE_URL` pointing to a `*_test` database — the conftest
  safety guard (`_resolved_db.endswith("_test")`) must never be bypassed
- Use shared `conftest.py` fixtures: ephemeral DB engine (NullPool), in-memory
  Valkey on DB 15, FastAPI `AsyncClient` via `ASGITransport`
- No real external calls — mock `GeminiAdapter`, `MSG91Adapter`, `RazorpayAdapter`,
  `GCSAdapter` at the adapter boundary, not deep inside services
- `pytest-asyncio` with `asyncio_mode = "auto"` — all test functions `async def`
- File placement:
  - `tests/unit/` — models, schemas, utils
  - `tests/integration/` — route flows, cross-module flows
  - `tests/modules/{domain}/` — domain-scoped suites
  - `tests/eval/` — AI golden fixtures
- Every test follows **AAA** (Arrange → Act → Assert), one logical assertion per test

#### Taxonomy

| Domain | Mandatory test cases |
|---|---|
| IAM | OTP send/verify happy path; OTP bypass `000000` dev-only; JWT issuance + rotation; refresh cookie HttpOnly + Secure + SameSite=Strict attrs; plan-guard rejects on plan limit; rate-limit sliding window triggers 429; Google verify + auto-link on email match; Google verify + 409 on `google_sub` collision |
| Catalog | CRUD happy path; dependency rules (SKU requires catalog); autofill AI call mocked returns expected shape; quality gate score thresholds (pass / fail boundary) |
| Category | Browse tree returns nodes; schema shape per category ID; smart-picker top-3 contract (returns exactly 3 with confidence scores); ETag cache hit returns 304 |
| Pricing | Apply-price P&L calc (commission=0%, shipping=constant per category, offline mode); negative margin detection |
| Export | Full pipeline happy path (catalog → ZIP); blocked-by-failed-precheck returns 422; round-trip validation failure surfaces field error; ZIP structure contains expected files |
| Billing | Razorpay webhook signature verify (valid + tampered); subscription state transitions (created → active → cancelled); mock-mode passthrough for dev |
| AI Ops | Budget cap hard-stop raises error at ceiling; cost tracker increments per call; guardrail rejects disallowed content; prompt-registry key lookup returns pinned template |

---

### 5.2 `meesell-frontend-testing`

**Trigger:** Any time Angular Karma/Jasmine specs are being written for the MeeSell
frontend.

#### Conventions

- Standalone component testing via `TestBed.configureTestingModule` with
  `imports: [ComponentUnderTest]`
- Mock services with `jasmine.createSpyObj` — never inject real services into
  component tests
- Flush signals with `TestBed.flushEffects()` before asserting signal-derived DOM state
- `HttpClientTestingModule` + `HttpTestingController` for components that trigger HTTP
- Spec file lives **adjacent** to source (`.spec.ts` next to `.ts`) — never in a
  separate `tests/` folder at the project root
- Test naming: `it('should {behaviour} when {condition}')`
- `ChangeDetectionStrategy.OnPush` components require explicit
  `fixture.detectChanges()` after state mutation

#### Taxonomy

| Layer | Mandatory test cases |
|---|---|
| UI Kit (20+ components) | Each component renders without error; `@Input()` bindings propagate to DOM; `@Output()` emitters fire on user interaction |
| Page components | Loading state: spinner visible when `loading()` is true; error state: snackbar triggered; happy-path: data from mock service renders correctly |
| Services | State mutation via `BehaviorSubject` / signal updates on API response; HTTP calls verified via `HttpTestingController`; error path calls `MatSnackBar.open()` |
| Auth guard | Redirects to `/login` when `AuthService.token()` returns null; passes through when token is valid |
| JWT interceptor | `Authorization: Bearer {token}` header attached when token present; request passes through unchanged when token is null |
| Catalog service | `list()` state transition; `create()` appends to signal; `update()` patches in place; subscription teardown on component destroy |

---

### 5.3 `meesell-e2e-testing`

**Trigger:** Any time Playwright E2E tests are being written for the MeeSell app.

#### Conventions

**Two-phase mandate (non-negotiable):**

1. **Exploration phase** — launch the full dev stack (`/mesell:dev`), use `agent-browser`
   to navigate the live app, discover real selectors, observe actual auth behaviour
   across shell → remote navigation. Deposit stable selectors into
   `.claude/agent-memory/meesell-e2e-test-writer/selector_registry.md`.
2. **Codification phase** — author Playwright `.spec.ts` files using the selectors
   found in phase 1. Never write selectors from memory or documentation.

Additional conventions:
- Page-object pattern — one class per remote (`CatalogPage`, `DashboardPage`, etc.)
  in `frontend/e2e/page-objects/`
- Pre-authenticate via `storageState` — `auth.setup.ts` runs OTP once, saves cookie to
  `storageState.json`; all tests depend on this setup project
- Target full federation stack: shell `:4200` + remotes `:4201–4206`
- No hardcoded ports — read all base URLs from `playwright.config.ts` environment
- Test files in `frontend/e2e/flows/`, one file per seller flow
- Every test must assert a **visible outcome** (DOM element, navigation, file download)
  not just a network call or console log
- Mark flaky tests with `test.fixme()` + reason rather than deleting them — they go
  into `federation_quirks.md`

#### Taxonomy — Critical Seller Flows (all must have coverage)

| Flow | File | What is asserted |
|---|---|---|
| Phone OTP onboarding | `onboarding.spec.ts` | OTP input → verify → plan screen → dashboard heading visible |
| Google Sign-In | `google-signin.spec.ts` | GIS button clickable → redirect → dashboard (no plan screen for linked account) |
| Catalog creation wizard | `catalog-creation.spec.ts` | Shell → catalog remote → all wizard steps complete → saved catalog appears in dashboard list |
| Image upload + precheck | `image-precheck.spec.ts` | Upload valid JPEG → quality gate result card visible with numeric score |
| Category smart-picker | `category-picker.spec.ts` | Description typed → top-3 suggestions appear → selection updates form field |
| Export download | `export.spec.ts` | Export button clicked → file download event triggered → downloaded file non-empty |
| Plan guard | `plan-guard.spec.ts` | Locked feature accessed on free plan → upgrade prompt visible, not a blank screen or 404 |
| Logout + back-nav guard | `logout-guard.spec.ts` | Logout → browser back → redirected to `/login`, protected page not rendered |

---

## 6. Agent Memory Structure

### 6.1 Directories

```
.claude/agent-memory/
  meesell-qa-coordinator/
    MEMORY.md
    qa_waves.md              ← wave history, coverage per wave, exit criteria met
    coverage_gaps.md         ← accumulated gaps across waves (survives between sessions)
    coordinator_patterns.md  ← recurring omissions in builder PRs (cross-wave learning)

  meesell-backend-test-writer/
    MEMORY.md
    test_files_authored.md   ← paths written, wave number, feature slug
    conftest_patterns.md     ← fixture reuse patterns, pitfalls observed
    deferred_coverage.md     ← items deferred with reason

  meesell-frontend-test-writer/
    MEMORY.md
    spec_files_authored.md
    testing_quirks.md        ← PrimeNG, signal, and federation-aware mock patterns

  meesell-e2e-test-writer/
    MEMORY.md
    selector_registry.md     ← stable selectors found via agent-browser
    flow_status.md           ← which flows are covered, flaky, or blocked
    federation_quirks.md     ← shell→remote navigation bugs observed live
```

### 6.2 Cross-Reading Protocol

| Agent | Reads at task start |
|---|---|
| `meesell-qa-coordinator` | `backend-coordinator/MEMORY.md`, `frontend-coordinator/MEMORY.md`, `ai-coordinator/MEMORY.md`, own `coverage_gaps.md` |
| `meesell-backend-test-writer` | `backend-coordinator/MEMORY.md`, `meesell-database-builder/MEMORY.md`, own `conftest_patterns.md` |
| `meesell-frontend-test-writer` | `frontend-coordinator/MEMORY.md`, `meesell-angular-component-builder/MEMORY.md`, own `testing_quirks.md` |
| `meesell-e2e-test-writer` | `frontend-coordinator/MEMORY.md`, `meesell-auth-builder/MEMORY.md`, own `selector_registry.md` + `federation_quirks.md` |

### 6.3 The `selector_registry.md` — Durable Exploration Asset

The E2E agent's most valuable memory file. Every `agent-browser` session deposits
stable selectors here. On subsequent waves the agent reads the registry first and only
launches `agent-browser` for flows or components not yet mapped — making each wave
cheaper than the last.

Example structure:
```markdown
## Shell (:4200)
- Logout: `[data-testid="nav-logout"]`
- Sidebar catalogs: `[data-testid="nav-catalogs"]`

## Catalog Remote (:4205 / mfe-catalog)
- Wizard next: `[data-testid="wizard-next"]`
- Category search: `[data-testid="category-search"]`
- Save draft: `[data-testid="save-draft"]`
```

### 6.4 The `coordinator_patterns.md` — Cross-Wave Learning

The QA coordinator's cross-wave learning log. Records recurring gaps in what builders
ship (e.g. *"backend-coordinator PRs consistently arrive without error-path tests for
new routes"*). This feeds into future wave specs automatically — each QA wave is
smarter than the last without any human intervention.

---

## 7. Delivery Plan

### 7.1 Artifacts

**Phase 1 — E2E scaffold (new directory)**
```
frontend/e2e/
  playwright.config.ts
  auth.setup.ts
  page-objects/
    shell.page.ts
    catalog.page.ts
    dashboard.page.ts
    export.page.ts
  flows/
    onboarding.spec.ts          (stub)
    catalog-creation.spec.ts    (stub)
    image-precheck.spec.ts      (stub)
    export.spec.ts              (stub)
    plan-guard.spec.ts          (stub)
    logout-guard.spec.ts        (stub)
```

**Phase 2 — 3 Skill files**
```
.claude/skills/
  meesell-backend-testing.md
  meesell-frontend-testing.md
  meesell-e2e-testing.md
```

**Phase 3 — 4 Agent spec files**
```
.claude/agents/
  meesell-qa-coordinator.md
  meesell-backend-test-writer.md
  meesell-frontend-test-writer.md
  meesell-e2e-test-writer.md
```

**Phase 4 — Memory bootstrap**
```
.claude/agent-memory/
  meesell-qa-coordinator/MEMORY.md
  meesell-backend-test-writer/MEMORY.md
  meesell-frontend-test-writer/MEMORY.md
  meesell-e2e-test-writer/MEMORY.md
```

**Phase 5 — Registry updates**
```
docs/status/feature_board_qa.md         (new — QA coordinator owns this)
docs/MEESELL_AGENT_REGISTRY.md          (update: 19 → 23 agents)
CLAUDE.md                               (update: agent roster table)
```

### 7.2 Build Assignment

| Phase | Builder |
|---|---|
| 1 — E2E scaffold | `meesell-infra-builder` |
| 2 — Skill files | `meesell-infra-builder` |
| 3 — Agent spec files | `meesell-infra-builder` |
| 4 — Memory bootstrap | `meesell-infra-builder` |
| 5 — Registry updates | `meesell-infra-builder` |

All 5 phases land in a single PR:
`feature/qa-wave-infra/infra` → `feature/qa-wave-infra/integration` → founder merges
to `develop`.

### 7.3 Artifact Count

| Category | Count |
|---|---|
| New agents | 4 |
| New skills | 3 |
| New memory directories | 4 |
| New E2E scaffold files | ~12 |
| Updated registry / docs files | 3 |
| **Total new / updated files** | **~26** |

---

## 8. First QA Wave — Expected Flow

Once the infrastructure lands on `develop`:

```
master session dispatches meesell-qa-coordinator
  "Run QA Wave 1 against: auth-otp, xlsx-export, catalog-wizard"
    → QA coordinator reads V1_FEATURE_SPEC + existing test coverage
    → Produces 3 test specs (one per specialist)
  master session dispatches:
    meesell-backend-test-writer   with backend test spec
    meesell-frontend-test-writer  with frontend test spec
    meesell-e2e-test-writer       with e2e spec + agent-browser exploration mandate
  QA coordinator runs merge-gate review on each of the 3 PRs
  feature/qa-wave-1/integration → founder merges to develop
```

---

## 9. Decisions Locked by This Spec

| Decision | Rationale |
|---|---|
| QA coordinator is Opus | Cross-domain strategy + merge-gate review requires reasoning depth |
| E2E writer is Opus (not Sonnet) | Module-federation topology + auth flows + page-object design is high-complexity |
| Two-phase E2E (explore then codify) | Prevents hallucinated selectors; `selector_registry.md` makes exploration cumulative |
| QA wave runs after features, not alongside | Zero friction on feature PRs; quality gate applies to a coherent feature batch |
| All 5 phases in one PR | The scaffold is useless without the agents; the agents are useless without the skills |
| `meesell-infra-builder` builds all phases | It owns doc authoring + config + dirs; no new agent type needed for bootstrap |
