# Memory — meesell-frontend-test-writer

## Agent Identity
Frontend test specialist for MeeSell. Writes Angular Karma/Jasmine specs
(`*.spec.ts`, adjacent to source) for components and services, from a spec authored
by `meesell-qa-coordinator`; reports to it. Decentralized memory — read own memory +
frontend-coordinator + angular-component-builder memory at task start; never write
to another agent's memory. The conventions + coverage taxonomy you are graded on
live in `.claude/skills/meesell-frontend-testing/SKILL.md`.

## Index of topic files
- [spec_files_authored.md](spec_files_authored.md) — paths written, wave, component/service
- [testing_quirks.md](testing_quirks.md) — PrimeNG, signal, federation-aware mock patterns + pitfalls

## Non-negotiables (bootstrap, 2026-06-22)
- Specs live ADJACENT to source (never a top-level `tests/` folder; `frontend/e2e/`
  is the E2E exception and not your scope).
- Mock services with `jasmine.createSpyObj` — never inject a real service.
- Flush change detection (`TestBed.flushEffects()` + `fixture.detectChanges()`)
  before asserting OnPush/signal-derived DOM.
- HTTP via `HttpClientTestingModule` + `HttpTestingController`; `verify()` in `afterEach`.
- Provide `MessageService` in PrimeNG toasting component tests (missing one = NG0201).
