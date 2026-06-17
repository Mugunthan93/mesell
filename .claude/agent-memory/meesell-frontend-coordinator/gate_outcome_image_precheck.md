# gate_outcome_image_precheck — meesell-frontend-coordinator

## Session mesell-image-precheck-frontend-session-1 — 2026-06-11 — HYBRID STEP 3 (merge-gate review) — VERDICT PASS

### What this gate did
- Reviewed `feature/image-precheck-frontend` @ e1c1cf6 (base origin/develop dd5ae0d) — both specialists' serial output (service-builder 9f30dc8/4571a89/5cc77aa, component-builder 8e2b1f7/daa0c40/e1c1cf6).
- Re-ran build + tests in worktree /tmp/mesell-wt/image-precheck-frontend INDEPENDENTLY (skeptical). 0 discrepancies vs specialist reports.
- VERDICT: PASS. Opened flat-lane founder-gate PR `feature/image-precheck-frontend` → develop (mirrors AI slice #122). Lead did NOT approve (D1).

### THE BIG ONE — this slice was a WIRE-NOT-BUILD
The image-uploader UI shell already existed (Waves 3-5 SIMULATION). STEP-1 audit correctly reframed FEATURE_PLAN's "create component" rows as "(a) create image.service.ts (b) rewire off SIMULATION onto backend contract". Same shape as the smart-picker-wiring PORT (#98). The 7 gaps G1-G7 were all wiring/contract gaps, not greenfield.

### Re-run evidence (the load-bearing numbers)
- Build mfe-catalog production: GREEN 2.777s (≤90s D12). image-uploader lazy chunk 16.65 kB raw / 4.22 kB transfer.
- `ng test frontend` CI=true: 48 files / 521 tests / 0 fail / 0 skip. Baseline 47 files on develop +1 image.service.spec.ts (15 svc tests). image-uploader.component.spec.ts rewritten in place (no file-count change).
- ONLY the `frontend` project has a test target (@angular/build:unit-test). `ng test mfe-catalog` ERRORS "Project target does not exist" — remotes have NO test target; all apps/**/*.spec.ts are discovered under the frontend target's `../apps/**` glob. RECORD THIS for every future apps/-resident slice gate.

### Worktree build env gotcha (NEW resolution path — record)
- Fresh worktree `pnpm install --config.dangerously-allow-all-builds=true` said "Already up to date" and did NOT extract the esbuild native binary (top-level node_modules/esbuild absent). `pnpm rebuild esbuild …` ALSO failed to extract.
- ROOT CAUSE: the worktree node_modules is sparse (20 top-level entries, .bin/ng is a real file not symlink) — a partial/hoisted layout. esbuild lives in `.pnpm/esbuild@0.27.3/node_modules/esbuild` + the platform pkg `.pnpm/@esbuild+darwin-arm64@0.27.3/.../bin/esbuild` (10MB native binary) BOTH present — only the host-side install symlink was missing.
- FIX THAT WORKED: `cd node_modules/.pnpm/esbuild@<ver>/node_modules/esbuild && node install.js`. The esbuild JS shim resolves the platform binary at runtime via its package, and @angular/build:application invokes esbuild via the JS API — so the platform pkg being present is what matters; install.js just wires the host symlink. Build worked after this. Multi-project workspace → must name the project: `ng build mfe-catalog` (the image code) NOT bare `ng build`.

### Deviation adjudications (1-5) — ALL ACCEPT (one with follow-up)
1. [svc] recursive Observable+setTimeout poll, NOT RxJS expand/timer — ACCEPT. Bounded (MAX_POLLS=6), backoff 1→2→4→8→16→30s, teardown clears timer + httpSub.unsubscribe; leak-test (unsub-before-first-poll) passes. Idiomatic expand/timer not required.
2. [cmp] plain typed-fn trackers in spec Section B (not vi.fn generics) — ACCEPT. Section A pure-fn model tests = the REAL exhaustive coverage (logic extracted to image-uploader.model.ts, pure TS, no TestBed). Section B stand-ins test reimplemented inline logic, NOT the component (weak — recorded). House pattern: ZERO `createComponent` across ALL mfe-catalog specs; only category.service + image.service use TestBed (service-only). TestBed+PrimeNG-standalone crash is the documented reason. Consistent.
3. [cmp] mee-empty-state icon+message (not title/description) — ACCEPT. Verified vs libs/composites/empty-state: inputs are `icon`(req)+`message`(req)+optional `cta_label`. Correct.
4. [cmp] onReupload() `new File([], 'reupload-N')` placeholder — ACCEPT WITH FOLLOW-UP. resetSlot + re-upload-with-correct-idx asserted, but a zero-byte File fails backend multipart at runtime. Real file-picker re-trigger = UI wiring item (ui-styler / Wave-6). NOT a merge blocker: founder-gate PR is not a prod merge; rest of wiring correct. LOGGED as Wave-6 follow-up.
5. [both] screenshots NOT captured — ACCEPT (founder-noted). No headless browser in build env. Consistent with all SP01-07 (in-browser mount handed forward). PR body notes it.

### Convention verifications (all PASS)
- 0 primeng outside ui-kit in changed files; 0 localStorage (FE-D5 in-memory token via auth.getToken()); 0 SIMULATION/setInterval/createObjectURL remnants.
- 0 LIVE old-precheck-key code — the only hits are migration comments + spec ABSENCE-assertions (expect(PRECHECK_KEYS).not.toContain('jpeg_format')). Backend keys jpeg_valid/color_space/resolution_pass/white_background/watermark_check exact.
- tsc strict + strictTemplates ON; OnPush + standalone:true; Wave-7 JSDoc interceptor migration note in image.service.ts.
- NO ESLint config exists in the frontend workspace → CI gate-3 lint is not wired for it; `noUnusedLocals` NOT set in tsconfig. So the ONE nit (unused `DestroyRef` import in image-uploader.component.ts) does NOT break build/CI — cosmetic. Record for a future lint-enable chore.

### Founder rulings consumed
- R-IP-A: dispatch-now lane (FEATURE_PLAN, not Wave-D sequencing); manual Bearer + Wave-7 JSDoc note. SATISFIED.
- R-IP-B: backend contract authoritative, one-way UI remap. SATISFIED (model.ts remap block + PRECHECK_KEYS backend order).
- G3 (AI lane): fix_hints = frontend static map; canonical wording §968/§F5 (amended by AI lead in PR #122). SATISFIED in PRECHECK_HINTS.

### WAVE-6 CROSS-REF (critical — do-not-double-dispatch)
This branch IS what wave6_api_wiring/MASTER_PLAN.md calls `wave6-images` (Wave D lane 1), landed EARLY per R-IP-A. When Wave 6 founder-approves and Wave D dispatches, image FE wiring MUST be skipped — it is DONE here. Noted in board row + PR body + the Wave-6 PENDING row should reference this when it activates.

### Records on this branch (ride the founder-gate PR)
- docs/status/feature_board_frontend.md row → IN REVIEW (founder gate) + Wave-6 cross-ref note.
- docs/status/STATUS_FRONTEND.md gate block.
- this memo.
