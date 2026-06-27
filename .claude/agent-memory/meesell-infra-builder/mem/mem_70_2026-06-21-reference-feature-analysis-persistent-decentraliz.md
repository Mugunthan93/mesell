## [2026-06-21] reference — Feature analysis: Persistent decentralized agent memory (CC feature)
Audit of the live `.claude/agent-memory/` ecosystem for adoption assessment:
- 171 tracked .md files, 2.9MB, all COMMITTED to git (not gitignored).
- Bloat: component-builder MEMORY.md=3045L, services=2392L, backend=1441L, infra(self)=1342L. No markdown-link index pattern in use (0 links in infra index) despite spec calling for "individual topic files indexed by MEMORY.md".
- Entry-type tags (user/feedback/project/reference) barely used: 6 total across whole fleet → tags not enforced.
- Staleness: 7 agent memories untouched since ≤2026-06-14 (xlsx-parser 06-05, prompt-engineer 06-10, legal 06-11, ai-coord/image-precheck 06-12, category-picker 06-14).
- REAL RISK for our git model: memory is committed + we run worktree-per-group → two worktrees can append to the same MEMORY.md → merge conflicts / lost learnings on the develop sync. Mitigation = per-session dated append files + index links, or move agent-memory to .gitignore with a periodic curated commit.
- Infra angle: this is dev-machine-local, ZERO GCP spend, zero RAM cost (plain markdown reads). Does NOT touch K3s/Terraform. Remote/cloud execution (the RAM-ceiling fix) would still read these files fine.

---
