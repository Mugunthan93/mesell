# Dev Environment Manager (`tools/meesell_env.py`)

A RAM-budgeted, port-isolated dev-environment manager for the 8 GB dev machine.
Run multiple worktrees' frontends + backends side by side without esbuild
deadlocks or swap thrash.

> Stdlib-only Python 3 CLI. It shells out to `ng` / `node` / `uvicorn` for the
> actual build/serve work. No new dependencies.

---

## The core idea

Serving a built Angular app (static `serve.js`) is cheap. **Building** is the RAM
spike. So this tool:

- **Statically reserves** a deterministic port block per worktree (the *slot* model).
- **Runs processes dynamically** inside a conservative RAM budget.
- **Serializes all builds** behind one machine-wide lock — only one `ng build` at a time.
- **Reuses untouched MFEs** from a shared baseline. A worktree only rebuilds the
  shell *if it touched it* plus the MFEs it actually changed.

### Why the shell almost never needs a rebuild

The shell loads its federation manifest **at runtime**:

```ts
// frontend/apps/shell/src/main.ts
initFederation('federation.manifest.json')  // origin-relative fetch
```

That manifest maps each `mfe-*` remote to a `remoteEntry.json` URL. Because it is
fetched at runtime (not baked into the bundle), we can reuse a **single baseline
shell build** and only swap the manifest per-env. So if your worktree did not
touch `apps/shell`, the tool serves a per-slot **copy** of the baseline shell
dist with a generated manifest — **no shell rebuild**.

> Hard rule (learned from a prior outage): the per-env manifest is **generated at
> runtime and never committed**. Committing worktree-pinned ports into
> `federation.manifest.json` previously broke the shell. The generated copies are
> gitignored.

---

## Port scheme (deterministic, persisted)

Each worktree gets a **slot** (int, 0–9), persisted in `.nexus/env-ports.json`
and reclaimable. **Slot 0 is the baseline** (the worktree on `develop`). New
worktrees get the lowest free slot.

For slot `N` (stride 10):

| Role        | Port              |
|-------------|-------------------|
| backend     | `8000 + N*10`     |
| shell       | `4200 + N*10`     |
| `mfe[i]`    | `4201 + N*10 + i` |

`i` = index of the MFE in **sorted** `frontend/apps/mfe-*` order. With ~7 MFEs a
slot occupies `420(1..7)+N*10`, comfortably inside the stride of 10 — no collisions.

Examples:

| Slot | Worktree           | backend | shell | mfes        |
|------|--------------------|---------|-------|-------------|
| 0    | `mesell` (develop) | 8000    | 4200  | 4201–4207   |
| 1    | first feature wt   | 8010    | 4210  | 4211–4217   |
| 2    | second feature wt  | 8020    | 4220  | 4221–4227   |

This formalizes the prior ad-hoc convention (master `:4200`/`:8000`,
gauth-live `:4210`/`:8010`).

---

## RAM guard (conservative — founder-locked)

`up` and any build are **refused** if either trips:

- free RAM `< 1500 MB`, or
- swap used `> 70%`.

Stats come from `vm_stat` (page size parsed from its header, not assumed) and
`sysctl vm.swapusage`. On refusal the tool prints live free-RAM/swap and suggests
a `down <idle-env>`.

---

## Commands

```
meesell_env.py up <worktree> [--mfe a,b,...] [--stub]
meesell_env.py down <worktree>
meesell_env.py baseline up|refresh [--stub]
meesell_env.py status
meesell_env.py gc
meesell_env.py ports <worktree>
```

`<worktree>` is the **directory basename** from `git worktree list`.

### `up <worktree> [--mfe a,b]`
1. Look up / assign the slot.
2. **Budget-check first** — refuse if RAM is tight.
3. Decide touched MFEs:
   - `--mfe a,b` → explicit list (validated against discovered apps), **or**
   - omitted → inferred from `git diff --name-only origin/develop...<branch>`
     scoped to `frontend/apps/`. None → pure-baseline shell.
4. Generate the per-env manifest: touched MFEs → this slot's local ports; all
   others → baseline (slot 0) ports.
5. **Build under the global lock** (one at a time; `pkill esbuild` between builds):
   only shell-if-touched + touched MFEs.
6. Serve everything static via `serve.js` on the slot's ports.
7. Backend: start `uvicorn --reload` on the slot's backend port **only if backend
   was touched**; otherwise point at the baseline backend.

### `down <worktree>`
Stops the env's tracked processes, removes its per-slot shell copy, **keeps the
slot reserved**.

### `baseline up | refresh`
Builds develop's shell **+ all MFEs** once (the shared fallback) and serves them
on slot 0. Run this before bringing up any worktree that doesn't touch every MFE.

### `status`
Table of running envs (worktree, slot, role, port, PID, alive) + live free RAM
and swap%, plus all slot reservations.

### `gc`
Stops orphaned/dead tracked processes and prunes slot reservations for worktrees
that no longer exist (`git worktree list`).

### `ports <worktree>`
Prints the assigned port block.

---

## Typical workflow

```bash
# One-time per session: build + serve the shared baseline (develop).
python3 tools/meesell_env.py baseline up

# Bring up a feature worktree — only its touched MFEs rebuild; the rest federate
# from the baseline. Backend reused from baseline unless the branch touched it.
python3 tools/meesell_env.py up my-feature-wt
# -> shell on :4210, touched mfes on 421x, untouched on 420x (baseline)

# Check what's running and how much RAM is free.
python3 tools/meesell_env.py status

# Free RAM for another env.
python3 tools/meesell_env.py down my-feature-wt

# Clean up dead processes + reservations for removed worktrees.
python3 tools/meesell_env.py gc
```

Smoke-test the orchestration without spending RAM on real builds with `--stub`.

---

## Generated files (all gitignored)

| Path                                   | Purpose                                  |
|----------------------------------------|------------------------------------------|
| `.nexus/env-ports.json`                | worktree → slot registry (persisted)     |
| `.nexus/env-state.json`                | running env → PIDs/ports/dist roots      |
| `.nexus/.build.lock`                   | `flock` target — global build mutex      |
| `.nexus/serve-<port>.log`              | serve.js logs                            |
| `.nexus/backend-<port>.log`            | uvicorn logs                             |
| `.nexus/shell-dist-slot-<N>/browser/`  | per-env baseline-shell copy + manifest   |
| `<served-dist>/federation.manifest.json` | generated per-env runtime manifest     |

All shared state lives under the **baseline (develop) tree's** `.nexus/`, so every
worktree shares one registry and one build lock.

---

## Verification (2026-06-21)

A live verification run of the env-manager produced the following findings.

### RAM guard — verified correct, no tuning needed

`ram_stats()` computes available memory as free + inactive + speculative pages
(not pure `Pages free`). A live run printed **2009 MB available** while pure-free
was only ~63 MB. The conservative guard (refuse if available < 1500 MB OR
swap > 70%) PASSED correctly and took the build lock. The feared "guard uses
pure-free and over-rejects" tuning bug does **not** exist.

### Dependency-tree gotcha + fix

A pruned sibling worktree (`razorpay-wave5`) left
`frontend/node_modules/@angular/cli` as a **dangling symlink** into the deleted
worktree's pnpm store, so `ng build` fails with `MODULE_NOT_FOUND` for every
caller in the develop tree.

Fix:

```bash
cd frontend && CI=true pnpm install
```

A bare `pnpm install` aborts with `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`
because it wants to purge the corrupted `node_modules` without a TTY; `CI=true`
is pnpm's prescribed non-interactive remedy. Verified afterward:
`node_modules/.bin/ng version` → Angular CLI 21.2.14, no error.

### `baseline up` — KNOWN ISSUE (does not yet work end-to-end)

As of 2026-06-21, `baseline up` builds the shell successfully (~3.2s) then
**deadlocks before the first MFE**: an `ng build` + `esbuild --service` child
hangs at ~0% CPU indefinitely (observed 8m19s). This is an esbuild
service-mode hang, **not OOM** — swap stayed flat at 18.9% and ~2 GB RAM was
free throughout, so the RAM guard was never the constraint. The
"pkill esbuild between builds" mitigation does not effectively clear the hung
service on this path. Only 1 of 8 apps (shell) built.

Safe-abort recovery: kill the orchestrator + `ng build` + `esbuild` PIDs, then
run `meesell_env.py gc` (note: `down` requires a worktree arg and is N/A to the
untracked baseline run); verify 0 listeners on ports 4200–4207 / 8000.

STATUS: fix pending — the serialized-build esbuild deadlock needs investigation
before `baseline up` is usable.
