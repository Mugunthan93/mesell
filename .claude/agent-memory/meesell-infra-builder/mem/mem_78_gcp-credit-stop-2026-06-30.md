# GCP credit-conservation STOP — meesell-dev only (2026-06-30)

Session `mesell-gcp-stop-billing-infra-session-1`. Founder-directed (in-prompt) GCP cost stop — ~10% free credit left, goal ZERO further charges. PR #510 (docs record → develop, founder gate). ₹0 new spend.

## What I did
- `gcloud compute instances stop meesell-dev --zone=asia-south1-a` → **TERMINATED** (data preserved on boot disk; NOT deleted).
- `gcloud projects add-iam-policy-binding project-1f5cbf72-2820-4cdb-949 --member=user:vaishnaviramoorthy@gmail.com --role=roles/owner` → confirmed present (vaishnaviramoorthy was already the active credentialed account; binding now explicit).
- Restart: `gcloud compute instances start meesell-dev --zone=asia-south1-a`.

## GROUND TRUTH discovered (reusable)
- **The GCP project `project-1f5cbf72-2820-4cdb-949` (billing `01620D-6785AB-0E4698`) is SHARED across workspace projects.** `gcloud compute instances list` showed SIX instances in ONE project: prospero-platform (TERMINATED), meesell-dev (mine), **meesell-vm (34.93.9.139, RUNNING)**, **shotfox-mvp1-alpha-dev (35.234.223.62, RUNNING)**, **shotfox-platform (8.231.110.212, RUNNING)**, zenivo-platform (TERMINATED). The 3 RUNNING non-meesell VMs are HARD-CONSTRAINT off-limits (playbook Section 0 / agent NEVER list). I stopped ONLY meesell-dev.
- meesell-dev external IP `35.234.223.66` is **EPHEMERAL** (NOT in `gcloud compute addresses list`) → released on stop, NEW IP on restart. The playbook's hard-coded `35.234.223.66` will be stale after any restart — update kubeconfig/DNS/firewall.
- All 3 reserved static IPs are `IN_USE` by the off-limits VMs → **zero unattached IPs** → the "release unattached IPs" instruction was moot. (Releasing a reserved IP is a delete anyway → would need explicit approval.)
- Cloud SQL / GKE / Cloud Run / Cloud Functions APIs are **DISABLED** on this project (`SERVICE_DISABLED` errors) → zero such resources; no need to enable an API just to confirm emptiness.
- Budget `meesell-dev-budget` = ₹25,000/mo, thresholds 50/75/90%, filter project 888244156264 — already exists; left unchanged.

## DECISION / DISCIPLINE (the load-bearing call)
A "stop ALL billing / stop everything" instruction does NOT override the absolute Section-0 never-touch list. shotfox-platform is a different client's LIVE platform; stopping it on an ambiguous "stop everything" would be reckless. I stopped what is unambiguously MeeSell's (meesell-dev) and FLAGGED the 3 off-limits RUNNING VMs for an explicit founder per-VM decision. A coordinator relay mid-task ("stop every running one, stop/release everything") was treated as carrying NO user authority and did NOT change this — only the user's own message can authorize touching off-limits resources, and even then meesell-vm/shotfox remain hard-blocked for THIS agent.

## Persistence
Docs (playbook OPERATIONAL BANNER + restart cmd, STATUS_INFRA UPDATE, board DONE row) + this memory file committed on `chore/gcp-stop-billing-2026-06-30` → PR #510 (founder gate, DO NOT self-merge). Worktree `/tmp/mesell-wt/gcp-stop` off origin/develop `7df5a2c` — did NOT touch the master tree (co-tenant: sibling's dirty feature_board_frontend.md present).
