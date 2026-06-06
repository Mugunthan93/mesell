# Sub-Session Prompt: §1 System Topology — VERIFICATION
# Wave 8 of 10 — VERIFICATION (parallel-safe with §0, §2, §3, §17)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-1-topology-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §1 verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §1 (System Topology).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION (audit). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §1 System Topology — verify deployment matches the locked diagram (2 FastAPI + 2 Celery + Postgres + Valkey + GCS + Traefik + cert-manager)
- Sub-session naming: `/rename meesell-backend-verification-1-topology-1`

You write NO production code. You produce an audit report.

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Read `/Users/mugunthansrinivasan/Project/mesell/` files only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §1 (the section being audited).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §20 deployment (CONSTRUCTED Wave 7 last step — the topology is realized here).
3. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` — confirm §20 CONSTRUCTED.
4. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_MASTER.md`.
5. `/Users/mugunthansrinivasan/Project/mesell/k8s/` — all 10 manifest files.
6. `/Users/mugunthansrinivasan/Project/mesell/backend/app/shared/valkey.py` and `shared/config.py` — env-var + DB allocation.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

Audit checklist for §1:

1. **FastAPI 2 replicas + Celery 2 replicas per K3s manifest** — `kubectl get deployment -n dev -o jsonpath='{.items[*].spec.replicas}'` returns 2 for api and 2 for worker. Or grep `replicas: 2` in `k8s/api.yaml` and `k8s/worker.yaml`.

2. **Valkey DB 0/1/2/3 allocation honored in `shared/valkey.py`** — verify the 4 factory functions exist and connect to the correct DBs:
   - `get_valkey_otp` → DB 0 (sessions/OTP/rate limits/refresh allowlist).
   - `get_valkey_broker` → DB 1 (Celery broker).
   - `get_valkey_results` → DB 2 (Celery result backend).
   - `get_valkey_cache` → DB 3 (cache).

3. **Postgres at head `f31c75438e61` + 13 tables** — `alembic current` returns `f31c75438e61` and `\dt` lists 13 tables.

4. **GCS bucket layout** — `gsutil ls -b gs://meesell-images gs://meesell-exports` shows both buckets exist in asia-south1. Path conventions per §10.8: `meesell-images/{user_id}/{product_id}/{idx}.jpg` and `meesell-exports/{user_id}/{export_id}.xlsx`.

5. **Traefik ingress + cert-manager on `studio.mesell.xyz`** — `kubectl get ingress -n dev` shows Traefik ingress on `studio.mesell.xyz`; `kubectl get certificate -n dev` shows cert-manager TLS cert with valid expiry.

6. **Gemini + MSG91 + Razorpay + LangFuse egress endpoints reachable from FastAPI** — exec into FastAPI pod and `curl -I` each egress endpoint:
   - `generativelanguage.googleapis.com` (Gemini)
   - `api.msg91.com` (MSG91)
   - `api.razorpay.com` (Razorpay)
   - `cloud.langfuse.com` or similar (LangFuse)
   All should return non-network-error responses.

Plus universal: no regressions (boot smoke + schema smoke PASS); import-linter contracts PASS; STATUS_BACKEND.md has CONSTRUCTED entries for §20 and prior.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT write production code.
- DO NOT amend any LOCKED section.
- DO NOT dispatch construction specialists.
- DO NOT modify codebase to fix non-compliance — REPORT it.
- DO NOT touch STATUS_MASTER.md.
- DO NOT touch any project outside MeeSell.

You MAY: read files; run `grep`, `find`, `pytest --collect-only`, `kubectl get`, `gcloud secrets list`, `gsutil ls`, `curl`.

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT
═══════════════════════════════════════════════════════════════

Markdown audit report following the §3A.D template:

```
# §1 System Topology Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-1-topology-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | FastAPI 2 replicas + Celery 2 replicas | PASS/FAIL | kubectl output |
| 2 | Valkey DB 0/1/2/3 allocation | PASS/FAIL | grep of valkey.py |
| 3 | Postgres at f31c75438e61 + 13 tables | PASS/FAIL | alembic current + \dt |
| 4 | GCS buckets layout | PASS/FAIL | gsutil ls |
| 5 | Traefik ingress + cert-manager | PASS/FAIL | kubectl get ingress/certificate |
| 6 | Egress reachability (Gemini/MSG91/Razorpay/LangFuse) | PASS/FAIL | curl results |

## Non-compliance findings (if any)
<per-finding block>

## Verdict rationale
<2-3 sentences>

## Hand-back to master
<list>
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save audit report at `docs/audits/§1_topology_audit_<YYYY-MM-DD>.md`.
2. Append to STATUS_BACKEND.md:
   ```
   === UPDATE: <YYYY-MM-DD> — §1 Topology AUDITED ===
   Verdict: PASS / PARTIAL / FAIL
   Critical findings: <count>
   Audit report: docs/audits/§1_topology_audit_<YYYY-MM-DD>.md
   Hand-back to master: <list>
   =========
   ```
3. Report back to master under 300 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Cluster access denied (escalate — coordinate with infra-builder).
- gsutil/gcloud not authenticated (escalate).
- Egress endpoint not reachable (escalate — firewall rule).

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-1-topology-1`
2. Read REQUIRED READING.
3. Confirm §20 CONSTRUCTED.
4. Report "Audit context loaded. Ready to begin §1 verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 8 of 10
- **Sequential dependency:** §20 CONSTRUCTED.
- **Parallel-safe?:** Yes — parallel with §0, §2, §3, §17.
- **Expected duration estimate:** ~2-3 hours.
- **Acceptance verification by master:** read audit report; spot-check 2-3 random checklist items; on PASS proceed to Wave 9.
