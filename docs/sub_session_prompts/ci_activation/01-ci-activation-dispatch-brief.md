# CI Activation — Session Dispatch Brief

**Session name:** `mesell-ci-activation-session-1`
**Date authored:** 2026-06-11 (master session, founder-approved parallel lane)
**Status:** READY — the founder is PRESENT in this session (his credentials + GitHub settings are required)

---

## What this session is

You are a dedicated sub-session to take MeeSell CI from **ready-not-active → ACTIVE**. The pipeline config is already merged and dormant (C-CI-1 discharged via PR #50: paths-filter matrix in `.github/workflows/ci.yml` + cloudbuild split). What's missing is the founder's 7-step activation — terraform-applied WIF + service account, GitHub variables/secrets, and branch-protection check contexts.

Dispatch `meesell-infra-builder` (foreground, so approval prompts reach the founder). **Only `meesell-*` agents may execute MeeSell work.**

## Required reading (in order)

1. `CLAUDE.md` (project root)
2. `docs/INFRASTRUCTURE_PLAYBOOK.md` — esp. §15 safe-deploy template ([MANDATORY GATE] dry-run rule) and the secret-discipline section
3. `docs/DEVOPS_ARCHITECTURE.md` — §5/§6/§9 (CI design, as updated by PR #50)
4. `.claude/agent-memory/meesell-infra-builder/MEMORY.md`
5. `infra/terraform/.tflogs/phase-e-plan-output.txt` — the pending plan (11 resources: GitHub WIF pool + `meesell-github-ci` SA)
6. `.github/workflows/ci.yml` + `cloudbuild.yaml` — what activates

## Step 0 — VERIFY CURRENT STATE FIRST

The 7-step list below was captured 2026-06-10; state may have drifted. Before anything: `terraform plan` to see what's genuinely pending, check GitHub repo variables/secrets via `gh api` (names only — NEVER values), check whether `main` already has protection/check contexts, and check whether the setup branch (`claude/meesell-project-setup-Tl7DS`) still exists/is already merged. Skip steps already done.

## The activation steps (founder drives; agent guides + verifies)

1. Review the plan: `infra/terraform/.tflogs/phase-e-plan-output.txt`
2. `cd infra/terraform && terraform apply -var-file=environments/dev.tfvars`
   **KNOWN GOTCHA:** stale GCP ADC credentials — if apply fails with auth errors, refresh first (`gcloud auth application-default login`, or the `GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)"` workaround).
3. `terraform output github_wif_provider_name` → GitHub repo **variable** `GCP_WIF_PROVIDER`
4. `terraform output github_ci_sa_email` → GitHub repo **variable** `GCP_CI_SA_EMAIL`
5. Founder creates a **low-quota Gemini API key** → GitHub **secret** `GEMINI_API_KEY_CI`
6. Protect `main`: require the CI status checks (capture the exact check-context names after the first run — see step 8)
7. Fire the first pipeline (push/PR to `main` per ci.yml triggers; if the old setup branch is the vehicle, founder merges it)
8. **After the first green run**: capture the real check-context names and add them to `main` (and evaluate for `staging`/`develop`) branch protection — this is the carried item from session 2.

## Hard constraints

- **NEVER print secret values** — names and resource IDs only. Terraform output values go straight into GitHub settings, not into the transcript where avoidable.
- **No cluster mutations** — this session touches terraform (WIF/SA only) + GitHub settings. The K3s cluster, k8s manifests, and DNS are OUT of scope.
- **Parallel lanes live**: frontend Wave 1 (SP02/SP03), AI, and Legal sessions are running. Do not touch `frontend/`, `docs/legal/`, AI surfaces, or their status files.
- Cost note: WIF + SA are ₹0; the Gemini CI key should be quota-capped (founder sets the cap).
- If terraform wants to change resources beyond the 11 planned, STOP and show the founder the diff before applying.

## Session end

Update `STATUS_INFRA.md` (UPDATE block: what flipped active, first-pipeline result, check contexts captured) + `feature_board_infra.md` + infra memory. Report: which steps were already done, which executed, the first pipeline verdict, and any follow-ups (e.g., check contexts still pending a first run).
