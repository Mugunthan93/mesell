# Runbook — Auth Secret Rotation (`REFRESH_TOKEN_PEPPER`)

**Owner:** `meesell-infra-builder` (infra lead)
**Feature:** auth-otp (FE-D5) — Feature 1 of 9
**Scope:** rotation of the `refresh-token-pepper` GCP Secret Manager secret, plus
emergency mass-revocation of active refresh sessions.
**Companion docs:** `BACKEND_ARCHITECTURE.md §4.B` (FE-D5 HMAC-with-pepper amendment),
`docs/plans/features/auth-otp/FEATURE_PLAN.md` (Risk register R5),
`docs/INFRASTRUCTURE_PLAYBOOK.md` (secret + deploy procedures).

> **Apply at NORMAL DEPLOY TIME.** Nothing in this runbook is executed during the
> manifests/docs authoring session. Every cluster/Secret-Manager command below is a
> deploy-time operation, run by whoever owns the deploy window.

---

## 0. Background — why `REFRESH_TOKEN_PEPPER` rotation is delicate

The refresh-token allowlist in Valkey DB 0 is keyed by an **HMAC-SHA256 digest of the
refresh token under the pepper** (live code — `backend/app/core/auth.py::refresh_allowlist_key`):

```
cache:refresh:{ hmac_sha256(refresh_token, REFRESH_TOKEN_PEPPER) }
```

The pepper is the HMAC key. It follows that:

- **Rotating the pepper changes the digest of every existing refresh token.** After a
  rotation, an in-flight refresh cookie hashes to a *different* key than the one stored
  in Valkey, so the allowlist lookup misses → `RefreshInvalidError` → the user is forced
  to re-login.
- The blast radius of a naive (hard-cutover) rotation is therefore **every currently
  active session**, bounded by how long allowlist entries live: `REFRESH_TOKEN_TTL_SECONDS`.

| Env | `REFRESH_TOKEN_TTL_SECONDS` | Worst-case forced-relogin window after hard cutover |
|-----|----------------------------|-----------------------------------------------------|
| dev | 120 (2 min) | trivial — sessions expire in 2 min anyway |
| staging | 300 (5 min) | trivial |
| prod (V1.5) | 604800 (7 days) | **unacceptable** — up to 7 days of users logged out |

This is FEATURE_PLAN Risk **R5**.

> **Current implementation note (read before prod):** as of 2026-06-11 the live key
> derivation is **version-tagged** — `cache:refresh:v{N}:{digest}` (see
> `backend/app/core/auth.py::refresh_allowlist_key`), and the dual-pepper read fallback
> (`validate_refresh_allowlist`) is implemented. The §2 grace-window scheme below is
> therefore **executable** (dual-pepper-rotation feature). For dev/staging the
> natural-expiry path in §1 remains the simplest routine (TTL is seconds/minutes); the §2
> grace window is what makes a **prod** rotation zero-downtime instead of a 7-day hard
> cutover. Legacy unversioned `cache:refresh:{digest}` keys (if any predate the change)
> expire naturally within `REFRESH_TOKEN_TTL_SECONDS` — no manual migration required.

---

## 1. Routine rotation — dev / staging (natural-expiry, no version tag)

Use this path whenever `REFRESH_TOKEN_TTL_SECONDS` is short (dev=120s, staging=300s).
Because every allowlist entry self-expires within the TTL, a plain pepper bump plus a
rolling restart causes at most `REFRESH_TOKEN_TTL_SECONDS` of re-logins — negligible in
non-prod.

**Pre-flight**

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
gcloud auth list                                    # confirm vaishnaviramoorthy@gmail.com active
gcloud config get-value project                     # project-1f5cbf72-2820-4cdb-949
gcloud secrets versions list refresh-token-pepper \
  --project=project-1f5cbf72-2820-4cdb-949 --filter="state=ENABLED"
```

**Step 1 — add a new pepper version (does NOT disable the old version)**

```bash
# Generate a fresh 32-byte pepper, no trailing newline. Keep a chmod-600 local backup.
NEW_PEPPER="$(openssl rand -hex 32)"
printf '%s' "$NEW_PEPPER" | install -m 600 /dev/stdin ~/.meesell-secrets/refresh-token-pepper.new
printf '%s' "$NEW_PEPPER" | gcloud secrets versions add refresh-token-pepper \
  --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
unset NEW_PEPPER
```

`latest` now points at the new version; the old version stays `ENABLED` (rollback safety).

**Step 2 — refresh the `backend-secrets` k8s Secret in the target namespace**

The app reads the pepper from the `backend-secrets` Secret via `envFrom`, not directly
from Secret Manager. Re-materialize that one key from SM `latest`:

```bash
NS=dev   # or: staging
PEPPER="$(gcloud secrets versions access latest --secret=refresh-token-pepper \
            --project=project-1f5cbf72-2820-4cdb-949)"
kubectl -n "$NS" patch secret backend-secrets --type merge \
  -p "{\"stringData\":{\"REFRESH_TOKEN_PEPPER\":\"$PEPPER\"}}"
unset PEPPER
```

(Never echo `$PEPPER` to a log. The `patch` above keeps every other key untouched.)

**Step 3 — roll the API + worker deployments so pods pick up the new env value**

```bash
kubectl -n "$NS" rollout restart deployment/api deployment/worker
kubectl -n "$NS" rollout status  deployment/api    --timeout=120s
kubectl -n "$NS" rollout status  deployment/worker --timeout=120s
```

**Step 4 — natural drain**

Existing allowlist entries (hashed under the old pepper) are now unmatchable and simply
expire within `REFRESH_TOKEN_TTL_SECONDS`. New logins after the rollout hash under the
new pepper. No manual Valkey cleanup is required. Affected users (any mid-session at
rollout time) silently re-login on their next refresh — at most one re-login each.

**Rollback (if the new pepper is bad):**

```bash
# Re-point backend-secrets at the previous SM version and roll back.
PREV="$(gcloud secrets versions list refresh-token-pepper \
          --project=project-1f5cbf72-2820-4cdb-949 \
          --filter="state=ENABLED" --format="value(name)" | sed -n '2p')"
PEPPER="$(gcloud secrets versions access "$PREV" --secret=refresh-token-pepper \
            --project=project-1f5cbf72-2820-4cdb-949)"
kubectl -n "$NS" patch secret backend-secrets --type merge \
  -p "{\"stringData\":{\"REFRESH_TOKEN_PEPPER\":\"$PEPPER\"}}"
kubectl -n "$NS" rollout restart deployment/api deployment/worker
unset PEPPER PREV
```

---

## 2. Zero-downtime rotation — prod (V1.5) — dual-pepper grace window

**Required before any prod rotation** because prod `REFRESH_TOKEN_TTL_SECONDS=604800`
(7 days) makes the §1 hard-cutover unacceptable (up to 7 days of forced re-logins).

The R5 mitigation (FEATURE_PLAN Risk register) is a **version-tagged keyspace with
dual-pepper reads during a grace window equal to `REFRESH_TOKEN_TTL_SECONDS`**:

1. **Version-tag the allowlist key** so a digest carries the pepper version that produced
   it: `cache:refresh:v{N}:{ hmac_sha256(token, pepper_vN) }`.
   - The backend writes new entries under the **current** pepper version `vN`.
   - On read/rotate, the backend tries `vN` first, then falls back to `vN-1`
     (`compare_digest` against both) for the duration of the grace window.
2. **Grace window length = `REFRESH_TOKEN_TTL_SECONDS`.** After a full TTL has elapsed
   since the rotation, every `vN-1` entry has expired, so the `vN-1` read path can be
   retired and `pepper_vN-1` can be disabled in Secret Manager.

**Operator sequence (when the backend supports versioned keys):**

| Step | Action | Result |
|------|--------|--------|
| 1 | `gcloud secrets versions add refresh-token-pepper` (new version `vN`) | `latest` = `vN`; `vN-1` stays `ENABLED` |
| 2 | Set `REFRESH_TOKEN_PEPPER` (= `vN`) **and** `REFRESH_TOKEN_PEPPER_PREVIOUS` (= `vN-1`) in `backend-secrets`; set `REFRESH_TOKEN_PEPPER_VERSION=N` | both peppers present in env |
| 3 | `kubectl rollout restart deployment/api deployment/worker` | pods write `vN` keys, read `vN`+`vN-1` |
| 4 | **Wait `REFRESH_TOKEN_TTL_SECONDS`** (7 days in prod) | all `vN-1` allowlist entries expire naturally; zero forced re-logins |
| 5 | Remove `REFRESH_TOKEN_PEPPER_PREVIOUS` from `backend-secrets`; `rollout restart` | read path is `vN`-only again |
| 6 | `gcloud secrets versions disable {vN-1}` | old pepper retired |

No user is logged out at any point: every live cookie is validatable under either `vN`
(issued after rotation) or `vN-1` (issued before, still within its TTL) for the whole
grace window.

> **Status:** implemented 2026-06-11 (dual-pepper-rotation feature). The version-tagged
> allowlist key (`cache:refresh:v{N}:{digest}`) + `REFRESH_TOKEN_PEPPER_PREVIOUS` /
> `REFRESH_TOKEN_PEPPER_VERSION` dual-read fallback are live in
> `backend/app/core/auth.py` (`refresh_allowlist_key` + `validate_refresh_allowlist`).
> The operator sequence above is now executable. Backend group PR #__BACKEND_PR__ →
> `feature/dual-pepper-rotation/integration`; founder-gate PR #__GATE_PR__ → `develop`.

---

## 3. Emergency mass-revocation — log every active user out NOW

Use only for a confirmed pepper/token compromise. **Blast radius: every active user is
logged out immediately** (their next API call 401s and the refresh interceptor bounces
them to `/login`). OTP login still works — this revokes sessions, it does not lock out
new logins.

**Option A — targeted DEL of refresh allowlist (preferred; leaves OTP state intact):**

```bash
NS=dev   # or staging / prod
# Valkey DB 0 holds both otp:* and cache:refresh:* keys. Delete ONLY refresh keys.
kubectl -n "$NS" exec -it statefulset/valkey -- sh -c \
  'valkey-cli -a "$VALKEY_PASSWORD" -n 0 --scan --pattern "cache:refresh:*" \
     | xargs -r -L 100 valkey-cli -a "$VALKEY_PASSWORD" -n 0 DEL'
```

- Uses `--scan` (cursor-based), **not** `KEYS` — `KEYS` blocks the single-threaded server.
- Deletes only `cache:refresh:*`; pending `otp:*` codes are untouched, so users can
  immediately re-login.
- **Blast radius:** all refresh sessions gone. Access JWTs already minted remain valid
  until their (short) `ACCESS_TOKEN_TTL_SECONDS` expiry — there is no server-side access
  JWT revocation by design; the short access TTL is the bound. After at most one access
  TTL, every request must refresh, and every refresh now 401s.

**Option B — `FLUSHDB` on DB 0 (heavier; also drops in-flight OTPs):**

```bash
kubectl -n "$NS" exec -it statefulset/valkey -- sh -c \
  'valkey-cli -a "$VALKEY_PASSWORD" -n 0 FLUSHDB'
```

- **Blast radius:** all refresh sessions gone **and** all pending OTP codes dropped
  (users mid-OTP must request a fresh code). DB 0 also holds rate-limit counters — those
  reset too. Use Option A unless DB 0 is itself suspected corrupted.
- Never run `FLUSHALL` — DB 1/2 are the Celery broker/result backend; flushing them drops
  queued background jobs.

**After either option:** no rollback. Affected users re-login via OTP. Record the
incident, and if a compromised pepper triggered this, rotate the pepper per §1/§2 in the
same window.

---

## 4. Pre-flight + validation checklist (every rotation)

- [ ] `gcloud auth list` shows `vaishnaviramoorthy@gmail.com` active
- [ ] `gcloud config get-value project` = `project-1f5cbf72-2820-4cdb-949`
- [ ] New pepper has **no trailing newline** — verify: `gcloud secrets versions access latest --secret=refresh-token-pepper --project=project-1f5cbf72-2820-4cdb-949 | tail -c 1 | xxd` (last byte must NOT be `0a`)
- [ ] Old SM version left `ENABLED` until grace window (§2) or rollback window (§1) closes
- [ ] `backend-secrets` patch touched **only** `REFRESH_TOKEN_PEPPER` (and `_PREVIOUS` in §2) — `kubectl -n "$NS" get secret backend-secrets -o jsonpath='{.data}' | python3 -c 'import sys,json;print(sorted(json.load(sys.stdin).keys()))'` shows the full key set unchanged
- [ ] `kubectl -n "$NS" rollout status deployment/api` and `deployment/worker` both report success
- [ ] Smoke after rollout: login → access protected route → wait an access TTL → confirm one silent `/auth/refresh` succeeds (proves the live pepper validates a freshly-issued token)
- [ ] No pepper value appeared in any shell log, commit, or `kubectl get -o yaml` output

---

## 5. Follow-ups / cross-lead

- **Backend (R5 / V1.5):** ~~implement the version-tagged allowlist key
  (`cache:refresh:v{N}:{digest}`) + `REFRESH_TOKEN_PEPPER_PREVIOUS` dual-read path so §2
  becomes executable~~ **DONE 2026-06-11 (dual-pepper-rotation feature)** —
  `backend/app/core/auth.py` `refresh_allowlist_key` (versioned) +
  `validate_refresh_allowlist` (dual-read fallback). §2 is now executable; prod rotation
  is zero-downtime, no longer incident-only. Owner: `meesell-auth-builder`.
- **Infra (dual-pepper-rotation):** provision `REFRESH_TOKEN_PEPPER_PREVIOUS` +
  `REFRESH_TOKEN_PEPPER_VERSION` secret refs in `k8s/secrets.yaml.example` + SM onboarding
  notes before the first prod rotation (inter-lead request opened on the backend board).
- **Infra (V1.5):** `external-secrets-operator` would let SM `latest` propagate to
  `backend-secrets` without the manual §1-Step-2 patch. Deferred per
  `secrets.yaml.example` note.
