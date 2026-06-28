## Deploy update path — `reset --hard FETCH_HEAD`, not `origin/main` (CI run-6 attempt-2, 2026-06-11)

**Bug:** the deploy job's VM manifest-refresh (`.github/workflows/ci.yml`, inside the IAP SSH `--command=`) has two branches — fresh `git clone --depth=1` (existing-clone absent) vs existing-clone update (`git fetch origin main` + `git reset --hard <ref>`). The fresh-clone path was exercised in attempt 1; the update path was NEVER exercised until attempt 2, where it died: `fatal: ambiguous argument 'origin/main': unknown revision` exit 128.

**Root cause:** `git clone --depth=1` creates a SHALLOW clone that has NO remote-tracking refs — there is no `refs/remotes/origin/main` on the VM checkout. So `git fetch origin main` updates `FETCH_HEAD` (works) but `reset --hard origin/main` references a ref that doesn't exist → fatal. A normal (non-shallow) clone would have `origin/main`; a shallow one does not.

**Fix (one line):** `git -C ~/mesell reset --hard origin/main` → `git -C ~/mesell reset --hard FETCH_HEAD`. The `git fetch origin main` line stays as-is — it populates `FETCH_HEAD` to exactly the just-fetched `main` tip. No escaping change: `FETCH_HEAD` has no shell-special chars inside the double-quoted SSH `--command=`. Branch `ci/deploy-reset-fetch-head` off origin/develop, PR to develop (do-not-merge — founder owns the develop gate).

**Rule:** any deploy/refresh script that does `git fetch <remote> <branch>` against a SHALLOW VM clone must reset to `FETCH_HEAD`, never to `<remote>/<branch>` — remote-tracking refs are absent in shallow clones. `FETCH_HEAD` is always the safe target immediately after a `git fetch`, and is correct in non-shallow clones too, so it's the universally-correct choice for fetch-then-reset.
