---
name: meesell-k3s-deploy-check
description: >-
  MeeSell's pre-deployment safety checklist and K3s manifest conventions. Use this skill
  WHENEVER you are about to deploy, are editing Kubernetes manifests, secrets, configmaps,
  ingress, or namespace config (k8s/), are touching the Dockerfile or CI/CD pipeline, or
  the user says "deploy", "ship to staging/prod", "roll out", "apply the manifest", or
  "update the cluster" — even if they don't say "K3s" explicitly. Apply it before any
  kubectl apply / rolling update to dev, staging, or prod. Do NOT use it for local-only
  docker-compose dev (defer to /mesell:dev).
---

# MeeSell K3s Deployment Conventions & Pre-Flight Checklist

These are the locked rules for deploying MeeSell onto its single-node K3s cluster on GCP
(asia-south1). They exist so a deploy never leaks a secret, never points at the wrong
namespace, and never takes the API down without a rollback path. They derive from
`CLAUDE.md` infra decisions (#1/#2/#6) and the project structure, which win.

## Architecture you are deploying into

Single-node K3s on the `meesell-dev` VM, namespaces `dev` / `staging` / `prod`, Traefik
ingress, cert-manager TLS. Services run as pods: API (2 replicas), Celery worker
(2 replicas), Postgres, Valkey, Frontend. Storage is GCS direct. AI is Gemini 2.5 Flash.

## The 8-point pre-flight checklist (run BEFORE any apply)

Treat each as a gate. If a gate fails, stop and fix before deploying.

1. **Namespace is explicit and correct.** Every `kubectl apply` names `-n <namespace>`.
   Never rely on the current context's default namespace — that's how prod gets a dev
   config. Confirm the target (`dev`/`staging`/`prod`) matches the intent out loud.

2. **No secrets in manifests or git.** `secrets.yaml` is never committed (only
   `secrets.yaml.example`). `.env`, `JWT_SECRET`, `GEMINI_API_KEY`, `MSG91_AUTH_KEY`,
   Razorpay keys, and the DB URL come from K8s Secrets, not inline `env:` values.

3. **Image tag is immutable and pushed.** Deploy a specific tag/digest, never `:latest`.
   Confirm the image is actually in the registry before the rolling update, or the pod
   will `ImagePullBackOff`.

4. **Migrations run before the API rolls.** Alembic `upgrade head` must complete against
   the target DB before new API pods serve traffic — otherwise new code hits an old
   schema. Migrations are backward-compatible (expand/contract) so old pods survive the
   overlap.

5. **Config parity.** The target namespace's ConfigMap has every key the new code reads
   (feature flags like `FEATURE_GOOGLE_AUTH_ENABLED`, `FEATURE_AI_AUTOFILL_ENABLED`). A
   missing key surfaces as a 500 at runtime, not at deploy time.

6. **Resource limits + health probes set.** Every Deployment has CPU/memory requests and
   limits (this is an 8 GB single node — an unbounded pod OOM-kills its neighbours) and a
   readiness/liveness probe hitting the `/health` endpoint.

7. **Rollout strategy is RollingUpdate with a rollback path.** Confirm
   `kubectl rollout status` is watched and you know the `kubectl rollout undo` command for
   the deployment before you start. No recreate strategy on the API (causes downtime).

8. **TLS + ingress intact.** cert-manager issuer matches the chart version in use (note:
   `installCRDs` for v1.14 vs `crds.enabled` for v1.15+ — the wrong key silently skips
   CRDs). Ingress host/path rules unchanged unless intentionally edited.

## Manifest conventions

- One manifest per concern (`api.yaml`, `worker.yaml`, `postgres.yaml`, …) — mirror the
  existing `k8s/` layout, don't invent a mega-file.
- Pin resource requests/limits on every pod.
- Reference secrets via `secretKeyRef`, config via `configMapKeyRef` — never literal values.
- Probes target `/health`.

## Safe apply sequence

```bash
# 1. Confirm context + namespace
kubectl config current-context
NS=staging   # set intentionally

# 2. Run migrations as a Job (waits to completion) BEFORE rolling the API
kubectl apply -n "$NS" -f k8s/migrate-job.yaml
kubectl wait -n "$NS" --for=condition=complete job/alembic-migrate --timeout=300s

# 3. Roll the API, then watch
kubectl apply -n "$NS" -f k8s/api.yaml
kubectl rollout status -n "$NS" deployment/meesell-api --timeout=180s

# 4. If it goes wrong:
kubectl rollout undo -n "$NS" deployment/meesell-api
```

## Finishing the task (Task Completion Protocol)

Two NON-NEGOTIABLE fleet rules gate "done" — full text in
`.claude/skills/meesell-task-completion-protocol/SKILL.md` (founder-ruled 2026-06-22):

- **Rule A — persist-on-finish.** Your durable outputs (memory, `docs/status/STATUS_*.md`,
  `docs/status/feature_board_*.md`, any manifest/spec you produced) must be **committed AND
  pushed** — on the feature branch (rides the PR) or via a `chore/<slug>-scribe` PR /
  git-plumbing for `.claude/`. Never leave them as uncommitted master-tree dirt.
- **Rule B — rebuild-localhost-on-merge.** A deploy/merge that reaches `develop` is followed
  by an affected-scope localhost rebuild so the dev stack matches `develop` (pull develop ->
  `python3 tools/meesell_env.py baseline refresh` for FE/federation, or restart
  `uvicorn --reload :8000` for backend -> verify ports via `meesell_env.py status` ->
  refresh the `:7700` dashboard). Docs-only merges skip the rebuild. See
  `docs/dev/ENV_MANAGER.md`. (This is localhost dev-stack hygiene; it is distinct from a
  real K3s `dev`/`staging`/`prod` cluster deploy, which still follows the 8-point checklist
  above.)

## Quick checklist before you finish a deploy task

- [ ] Namespace named explicitly on every command, matches intent
- [ ] Zero secrets in manifests/git; all via K8s Secrets
- [ ] Specific image tag, confirmed pushed (no `:latest`)
- [ ] Migrations applied + backward-compatible before API rolls
- [ ] ConfigMap parity for all new keys/flags
- [ ] CPU/mem requests+limits + `/health` probes on every pod
- [ ] RollingUpdate + known `rollout undo` command ready
- [ ] cert-manager CRD key matches chart version; ingress intact
