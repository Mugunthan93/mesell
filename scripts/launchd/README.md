# Nightly localhost preview updater (launchd)

Auto-updates the founder's **localhost preview** to the latest `develop` at **01:00 local
time** every night, so the merged work is already built and served by morning.

- **Script:** [`scripts/nightly-localhost-update.sh`](../nightly-localhost-update.sh)
- **launchd job:** `com.meesell.localhost-nightly` (this directory)
- **Owner:** meesell-infra-builder (Infra Lead)
- **Cost:** ₹0 — purely local. No cloud, no secrets, no production.

---

## What it does

Once a night, **only if** the master working tree
(`/Users/mugunthansrinivasan/Project/mesell`) is on a **clean `develop`**, it:

1. `git fetch origin` then `git pull --ff-only origin develop`
2. Rebuilds the frontend with the **memory-safe static path**
   (`pnpm run dev:build-static` — watchdog, one app at a time)
3. Restarts the 7 static preview servers on ports **4200–4206**
   (`pnpm run dev:serve-static`, launched detached in its own process group)

Open **http://localhost:4200** in the morning to see the latest merged work.

> It uses the **static** path on purpose. `pnpm run start:all` (7 live `ng serve`
> watchers, 3–5 GB) **hangs the 8 GB machine** — this job never uses it. The static path
> holds ~129 MB total. See `frontend/tools/dev/STATIC_DEV.md`.

The backend is **not** started by this job: the static preview mocks auth at the route
level, and keeping it frontend-only is what keeps it memory-safe. Start `make dev` yourself
if you need live API/OTP flows.

---

## Safety guards (why it's safe to leave running during active recovery work)

The master checkout is frequently parked on a feature branch or left dirty mid-session.
In any of these cases the job is a **strict no-op** — it logs a `SKIP` and exits 0:

| Condition | Behaviour |
|---|---|
| HEAD is **not** `develop` (e.g. `feature/section-3/frontend`) | `SKIP: master tree on '<branch>', not develop` — **no checkout, no switch** |
| Tracked working tree is **dirty** | `SKIP: working tree dirty` — nothing touched |
| `git fetch` fails (offline) | `SKIP` — no-op |
| `develop` diverged (not a clean fast-forward) | `SKIP: not a clean fast-forward` — **never force/reset/merge** |
| Already up to date | logs "up to date", skips the rebuild |

It **never** switches branches, stashes, resets, merges, or force-pulls. It only ever
**fast-forwards a clean `develop`**. It **never** touches any `/tmp/mesell-wt/section-*`
(or any other) worktree — it operates solely on the master checkout.

---

## Check the log

```bash
tail -f /Users/mugunthansrinivasan/Project/mesell/logs/nightly-localhost-update.log
```

Every run is timestamped. The detached preview servers' own output goes to
`logs/serve-static.out`. Both log files live under `logs/`, which is git-ignored.

---

## Run it once manually (to test)

Safe to run any time — the guards apply identically when run by hand:

```bash
bash /Users/mugunthansrinivasan/Project/mesell/scripts/nightly-localhost-update.sh
```

If the master tree is on a feature branch or dirty, you'll see a `SKIP` line and nothing
else happens. To exercise the full build+serve path, check out a clean `develop` first.

---

## Install / load the launchd job

launchd agents live in `~/Library/LaunchAgents` (outside the repo). Install with:

```bash
cp /Users/mugunthansrinivasan/Project/mesell/scripts/launchd/com.meesell.localhost-nightly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.meesell.localhost-nightly.plist
```

Verify it's registered:

```bash
launchctl list | grep com.meesell.localhost-nightly
```

After editing the plist, reload it:

```bash
launchctl unload ~/Library/LaunchAgents/com.meesell.localhost-nightly.plist
cp /Users/mugunthansrinivasan/Project/mesell/scripts/launchd/com.meesell.localhost-nightly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.meesell.localhost-nightly.plist
```

---

## Disable

```bash
launchctl unload ~/Library/LaunchAgents/com.meesell.localhost-nightly.plist
# optional: remove the copy
rm ~/Library/LaunchAgents/com.meesell.localhost-nightly.plist
```

To stop the running preview servers without disabling the job, kill the recorded
process group:

```bash
kill -TERM -"$(cat /Users/mugunthansrinivasan/Project/mesell/logs/.serve-static.pgid)"
```
