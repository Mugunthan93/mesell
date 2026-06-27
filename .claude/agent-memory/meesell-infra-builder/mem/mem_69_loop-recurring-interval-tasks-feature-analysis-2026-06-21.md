## /loop (recurring interval tasks) — feature analysis (2026-06-21)

Claude Code `/loop` = in-session recurring self-dispatch (run a prompt every N min / N turns). NOT OS cron.

MeeSell already has recurring automation: launchd `nightly-localhost-update.sh` (01:00), `devdb-backup` (02:00), CI `schedule:` cron, `.claude/scheduled_tasks.lock`. These are blind shell — `/loop` adds Claude judgment on top.

Best fits: (1) PR/board gate sweeper for the two-step git gate + 7-day stale-row sweep; (2) serial one-MFE-at-a-time rebuild loop (avoids 8GB esbuild deadlock vs parallel start:all); (3) recurring STATUS/memory sweep across 19 agents.

HARD CAVEATS: /loop is dev-orchestration ONLY — must NOT author code (only meesell-* agents touch code; loops dispatch into fleet). Each tick burns tokens (cost) — keep cadence coarse. Don't loop ng build at parallel — serialize. Keep loops in master session, never in a worktree (never git in master tree rule).

---
