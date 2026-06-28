## agent-memory size guard (FED/W10 prevention layer) — 2026-06-27

Session `mesell-agent-memory-size-guard-infra-session-1`. PR `chore/agent-memory-size-guard/infra` → develop (DO NOT MERGE — founder gate M5). Built a SessionStart WARN-ONLY hook + committed the reusable restructure/verify tooling. Closes `docs/GIT_WORKFLOW.md` **W10** ("memory files grow unbounded via append; compaction/rotation TBD"). It is the prevention layer so the PR #493 bulk restructure (8 fat MEMORY.md → lean index) never has to be repeated by hand. ₹0, dev-only.

### Files (5)
- `.claude/hooks/warn-agent-memory-size.sh` (new, +x) — the guard.
- `.claude/settings.json` (mod) — appended the guard as a SECOND SessionStart hook ALONGSIDE `heal-agent-memory-perms.sh` (heal stays first, not reordered).
- `tools/agent_memory/restructure_mem.py` + `verify_mem.py` (copied from /tmp, hardened) + `README.md` (new) — the remediation tooling the guard points offenders at.

### The metric (the load-bearing design choice)
Detect **inline prose**, NOT entry count — a lean index with many one-line `- [..](..)` entries is GOOD and must stay silent. A line is "prose" iff (beyond the first `IDENTITY_SKIP=12` lines) it is non-blank AND not: a heading `^#`, a blockquote `^>`, or an **index entry** = a list bullet carrying a markdown link. The index-entry test is `line ~ /^[ \t]*[-*][ \t]/ && line ~ /\]\(/` — i.e. "bullet AND contains `](`". 
- 🔴 GOTCHA: the restructured index lines are `- ⭐ [..](..)` where ⭐ = U+2B50 (bytes `e2 ad 90`). The naive `^[-*] \[` from the brief MISSES the star-prefixed lines → counts them as prose (backend-coordinator falsely showed 70 prose). Do NOT try to match the star bytes with `\xNN` in awk — **BSD/macOS awk does not honor `\xNN` regex escapes**. The byte-independent fix is "bullet + `](`": catches `- [..](..)` and `- ⭐ [..](..)` alike, and prose bullets (`- backend/app/x.py (405 LOC)`, `- **CurrentUser** — ...`) correctly stay prose (no `](`).
- Tables / code-fence lines / prose bullets all count as prose by design — they belong in `mem/` detail files.

### Thresholds: prose>120 OR total-lines>300 (both env-overridable: `MESELL_MEM_PROSE_MAX` / `MESELL_MEM_LINES_MAX`; `MESELL_MEM_IDENTITY_SKIP`)
Calibrated against the LIVE develop distribution (not the brief's suggested ~30, which would false-positive). Empirical prose counts: frontend-coordinator 433, scraper-maintainer 242, xlsx-parser 150, data-engineer 134 | **auth-builder 107** | prompt-engineer 56, ai-coordinator 45, qa-coordinator 25 | the 8 restructured 0–1. There is a natural gap **107→134**; the brief mandates auth-builder + qa-coordinator stay SILENT, so the prose threshold sits in that gap at 120. lines>300 is the backstop (catches a pathologically long file regardless of prose classification; also catches the old 1000–1400-line pre-restructure journals). Consequence: the guard targets EGREGIOUS drift (the class that bloated files to 1000+ lines) + the 4 genuinely-fat un-migrated journals, while tolerating the convention's "lazy per-agent migration" middle band (auth-builder/prompt-engineer/ai-coordinator).

### Validation evidence (all proven)
- Hook run on develop state: fires on exactly 4 (frontend-coordinator 433/619, scraper 242/367, xlsx 150/257, data-engineer 134/235); SILENT on all 8 restructured + auth-builder + qa-coordinator + prompt/ai + nexus-director; exit 0.
- Synthetic 200-prose file → fires (192/204). Old pre-restructure infra blob (`9efa43f^1`, 1430 lines) → fires (863/1430). Override `MESELL_MEM_PROSE_MAX=30` → auth-builder now fires (overridable proven). Both-thresholds-high → silent. 352-line pure-index (0 prose) → fires on lines-backstop. No agent-memory dir → silent. ALWAYS exit 0.
- Tooling: `restructure_mem.py` dry-run on frontend-coordinator = 620→62 lines, VERIFICATION PASSED, 0 files written. `verify_mem.py` on already-restructured infra + backend-coordinator = PASS, unaccounted=0.

### Reusable principles
- A SessionStart guard is the same warn-only/exit-0/fail-open contract as `heal-agent-memory-perms.sh` and the lifecycle hooks — warn to **stderr**, never block, never slow start (pure awk, no deps).
- When calibrating a threshold, MEASURE the live distribution and pick a value in the natural gap; document why; make it env-overridable. The brief's suggested number was a starting point, not a mandate.
- Targets glob = `agent-memory/meesell-*/MEMORY.md` PLUS `nexus-level-0-director/MEMORY.md` (the director dir has no `meesell-` prefix).
- Master tree was STALE (1431-line pre-restructure MEMORY.md) — I built + landed entirely from a fresh worktree off `origin/develop` (where `.claude/` is a real checkout), never the master tree. Appending memory to the stale master copy would have re-introduced the pre-restructure bloat.
