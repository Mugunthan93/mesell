---
name: meesell-ci-hardening-complete
description: CI/CD hardening drive (bg session mesell-dual-pepper-session-1) CLOSED 2026-06-13 — protection live, gates green, deploys from develop, all PRs landed
metadata:
  type: project
---

# MeeSell CI/CD hardening drive — CLOSED (2026-06-13)

Background session `mesell-dual-pepper-session-1` closed with zero open items. Final state:

- **Branch protection LIVE** on develop + main: 13 required contexts (5 backend gates + 8 frontend units). Build/Deploy/AI-eval/Nightly deliberately EXCLUDED (never report on PRs → would deadlock). `strict: false`, 0 reviews, `enforce_admins: false`.
- **FOUNDER RULING 2026-06-12**: dev-namespace K3s deploys fire from **develop** (push-only); main reserved for future staging/prod promotion, founder-gated. Every develop push (even docs-only) triggers build+deploy — `paths-ignore: docs/**` is a pending founder call (flagged in STATUS_INFRA).
- **Override discipline**: the one `--admin`-over-red authorization was #150-scoped and is SPENT. `--admin` on green PRs = mechanics only (single-account self-approval block). Never merge over red without a fresh founder grant.
- **Gate-4 saga closed**: PR #150 (Gate-1 event-loop fix, override-landed) → unmasked latent Gate-4 regression ("red hides red" skip-cascade) → PR #159 rejected pass 1, repaired loop 1, merged honestly → docs #157 + #162 landed. Ticket BE-CATALOG-G7-AUTOAPPLY-1 closed (test-stale, app conformed to G7).

**Why:** this memory closes the arc started in [[meesell-session-2-handoff]]/session-3 records — those describe in-flight CI work now finished.
**How to apply:** treat develop CI as fully protected + green baseline. Any future red on develop is NEW breakage, not legacy. Open founder-pending items live with the founder, not a session: paths-ignore docs/**, GEMINI_API_KEY_CI secret, PR #181 (PgBouncer, founder gate — MS parallel program, not this session's).

Key lessons recorded in lead memories: skip-cascade masking (re-baseline Gate 4 after any conftest change), middleware vs DI seam (`_otp_client` module singleton invisible to dependency_overrides), pytest-asyncio 0.24 loop model.
