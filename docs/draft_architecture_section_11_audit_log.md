> **STATUS: INTEGRATED** into docs/MVP_ARCHITECTURE.md (2026-06-04 evening). This file is archival only. See the canonical version in MVP_ARCHITECTURE.md.

# Section 11 — Audit Log and Autosave Events

**Status:** Draft — Backend Architect output, 2026-06-04
**Feeds into:** `MVP_ARCHITECTURE.md` (pending founder review before merge)

---

## 11.1 What Gets Logged

Every write that changes persistent state is an audit candidate. The rule is: **if a seller would care later that it happened, log it.**

| Event Type | Trigger | Logged |
|---|---|---|
| `product.patch` | `PATCH /api/v1/products/{id}` (includes autosave) | Yes |
| `product.export` | `POST /api/v1/exports` | Yes |
| `seller_profile.update` | `PATCH /api/v1/seller-profile` | Yes |
| `auth.login` | Successful OTP verify | Yes |
| `GET *` | Any read | **No** — too noisy, zero recovery value |
| AI suggestions (pre-accept) | Gemini response before seller accepts | **No** — PII surface, no durable value |
| OTP value | Any OTP send/verify | **No** — never stored, never logged |
| Password / JWT secret | N/A — we use OTP auth | **No** |

---

## 11.2 Schema

Append-only. No `UPDATE`, no `DELETE` path exists in the application layer. Archive-then-purge handles lifecycle (§11.5).

```sql
CREATE TABLE audit_events (
  id               BIGSERIAL PRIMARY KEY,
  user_id          UUID NOT NULL REFERENCES users(id),
  event_type       VARCHAR(40) NOT NULL,   -- "product.patch" | "product.export"
                                           -- | "seller_profile.update" | "auth.login"
  entity_type      VARCHAR(20),            -- "product" | "seller_profile" | "user"
  entity_id        UUID,                   -- null for auth.login
  diff_jsonb       JSONB,                  -- {"before": {...}, "after": {...}}
                                           -- null for events with no delta (e.g. auth.login)
  metadata_jsonb   JSONB,                  -- ip, user_agent, request_id, session_id
  occurred_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Primary query patterns (§11.8)
CREATE INDEX idx_audit_user_time   ON audit_events(user_id, occurred_at DESC);
CREATE INDEX idx_audit_entity      ON audit_events(entity_type, entity_id);
```

`diff_jsonb` stores only fields that changed. For `product.patch`, the before/after values use **canonical field names** (never Meesho column headers — respects CORE_PHILOSOPHY F8). Sensitive fields are scrubbed before insertion (§11.9).

---

## 11.3 Write Path

The application never writes to `audit_events` synchronously inside a request transaction. This avoids write amplification from the 10-second autosave cadence and prevents audit I/O from slowing the primary write path.

```
PATCH /api/v1/products/{id}
  │
  ├── 1. SQLAlchemy transaction → writes to products table → COMMIT
  │
  ├── 2. FastAPI middleware detects successful write (no exception raised)
  │       serialises {user_id, event_type, diff, metadata} → JSON
  │       pushes to Valkey DB 1 key: "audit:queue" (RPUSH, fire-and-forget)
  │
  └── 3. Celery worker (audit_flush_task, runs every 30 s)
          pops batch of ≤500 events from Valkey queue
          inserts via bulk INSERT INTO audit_events ... (single round-trip)
          acknowledges batch
```

**Critical constraint:** If the primary transaction is rolled back (validation error, constraint violation), the middleware does NOT push to the Valkey queue. Failures are never logged. The middleware checks response status >= 400 before enqueuing.

---

## 11.4 Autosave Coalescing

Raw autosave cadence: one `PATCH` every 10 seconds. For a seller filling a form for 30 minutes, that is 180 raw events for a single product. Stored naively, 1,000 sellers each working 30 min/day produces 5.4 million raw rows/day — clearly wrong.

**Coalescing window: 5 minutes, per (user_id, product_id).**

The Celery flush task applies this rule before inserting:

1. Pull all pending `product.patch` events from the queue.
2. Group by `(user_id, entity_id)`.
3. For each group, find events whose `occurred_at` falls within the same 5-minute bucket (floor to 5 min).
4. Collapse the group: `diff_jsonb.before` = before-value from the **earliest** event in the window; `diff_jsonb.after` = after-value from the **latest** event in the window. `occurred_at` = latest event timestamp. Intermediate states are discarded.
5. Insert one row per (user, product, 5-min window).

**Result:** A seller autosaving a product for 60 minutes generates at most 12 coalesced audit rows (60 min / 5-min window), not 360. The first and last value within each window are preserved for exact delta reconstruction.

Non-autosave events (`product.export`, `seller_profile.update`, `auth.login`) are **never coalesced** — each occurrence is a distinct audit fact.

---

## 11.5 Retention Policy

| Phase | Duration | Storage | Action |
|---|---|---|---|
| Hot | 0–90 days | PostgreSQL `audit_events` | Live, indexed, queryable |
| Warm archive | 91 days – 1 year | GCS `gs://meesell-audit-archive/YYYY/MM/` | Gzipped JSONL, one file per day |
| Expiry | > 1 year | — | Delete from GCS (unless legal hold flag is set) |

Archive job: Celery beat task runs nightly. Selects rows where `occurred_at < NOW() - INTERVAL '90 days'`, streams to GCS as gzipped JSONL, then hard-deletes from Postgres. Archive is immutable once written — no GCS object versioning overwrites. Legal hold is implemented by a Valkey key `audit:legal_hold:{user_id}` that the archive job checks before deleting.

---

## 11.6 Autosave Recovery: `product_drafts` Table

`audit_events` is the **immutable history**. It is NOT the recovery mechanism — it is too coalesced and too append-only for fast crash recovery. A separate table serves that purpose.

```sql
CREATE TABLE product_drafts (
  user_id     UUID NOT NULL REFERENCES users(id),
  product_id  UUID NOT NULL REFERENCES products(id),
  draft_jsonb JSONB NOT NULL,         -- full current field state, not a diff
  saved_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, product_id)
);
```

**Lifecycle:**
- On every successful `PATCH /api/v1/products/{id}`, the service layer upserts `product_drafts` with the full current field state (one row per product, ON CONFLICT DO UPDATE).
- On successful `POST /api/v1/exports`, the corresponding `product_drafts` row is deleted.
- On browser reload / crash recovery, the frontend calls `GET /api/v1/products/{id}/draft` which returns the `draft_jsonb` and re-hydrates the wizard.

`product_drafts` is mutable, low-latency, and ephemeral. `audit_events` is append-only, durable, and coalesced. They serve orthogonal purposes and must not be conflated.

---

## 11.7 Abuse Detection Signals

The same Celery flush task that coalesces audit events also feeds a rules engine. Rules are evaluated against **rolling counts in Valkey** (not against Postgres — latency must be sub-second).

| Signal | Rule | Response |
|---|---|---|
| Bot / automated fill | > 100 `product.patch` events/minute for a single user_id | Set Valkey key `abuse:bot:{user_id}` TTL 1 hour; API returns 429 |
| OTP brute force | > 10 failed OTP attempts/hour for a single phone | Set `abuse:otp:{phone}` TTL 1 hour; block further OTP sends |
| Scraper / mass create | > 1,000 `products` created in any rolling 24-hour window | Set `abuse:scraper:{user_id}` TTL 24 hours; alert ops Slack webhook |
| Unusual IP switch | Same session, IP changes mid-session | Log to `metadata_jsonb`, flag for manual review (no auto-block V1) |

All blocks are implemented as Valkey key checks in the `rate_limit.py` middleware — already on the request path for OTP rate limiting. No new middleware layer needed.

---

## 11.8 Query Patterns

Two primary access patterns, both served by the indexes defined in §11.2:

**Pattern A — Product history ("what changed on this product yesterday?"):**
```sql
SELECT * FROM audit_events
WHERE entity_type = 'product'
  AND entity_id   = :product_id
  AND occurred_at BETWEEN :start AND :end
ORDER BY occurred_at DESC;
-- Uses: idx_audit_entity
```

**Pattern B — User activity ("show all activity for user X"):**
```sql
SELECT * FROM audit_events
WHERE user_id    = :user_id
  AND occurred_at > NOW() - INTERVAL '7 days'
ORDER BY occurred_at DESC
LIMIT 100;
-- Uses: idx_audit_user_time (covering index)
```

Both are exposed as admin-only endpoints (`/api/v1/admin/audit`) behind an `is_admin` JWT claim check. Sellers do not have direct access to the raw audit table in V1; they see a simplified activity summary on the dashboard.

---

## 11.9 PII Safety in `diff_jsonb`

Before any event is pushed to the Valkey queue, a scrubber function strips or hashes fields that are sensitive:

| Field | Treatment |
|---|---|
| `phone` | Replace with SHA-256(phone + PII_SALT) — preserves abuse correlation without exposing the number |
| `fssai_license_number` | Redact to `[REDACTED-FSSAI]` |
| `gst_number` | Redact to `[REDACTED-GST]` |
| `otp` | Never reaches diff — OTP values are never written to products/seller_profile |
| All other fields | Stored as-is — product field values (title, description, price) have no PII concern |

`PII_SALT` is a per-deployment secret in `backend/.env` (`AUDIT_PII_SALT`). It is rotated annually. The hash is one-way: sufficient to detect "same phone across two accounts" in abuse analysis, but not reversible by a DB read.

---

## 11.10 Volume Estimate

| Variable | Value |
|---|---|
| Active sellers (V1 target) | 1,000 |
| Raw `product.patch` events per seller per day | ~10 (2 products, 5 autosave sessions each) |
| After 5-min coalescing | ~3 events/seller/day |
| Total coalesced events/day | 3,000 |
| Total events/year | ~1.1 million |
| Row size estimate | ~800 bytes avg (UUID + JSONB diff) |
| Annual storage (Postgres) | ~880 MB — trivially within single-node budget |

At 1M rows with the two indexes defined above, both query patterns (§11.8) return in < 5 ms on the existing `meesell-dev` VM. No partitioning required until seller count exceeds 50,000.

---

## Dependencies and Constraints

- `audit_events` MUST be append-only. Application code contains no `UPDATE` or `DELETE` on this table. Archive-and-purge is the only deletion path, and it runs outside the application (Celery beat, admin-only).
- `product_drafts` is separate from `audit_events`. Do not merge them.
- PII scrubbing (§11.9) is mandatory on every event before queue push. It is not optional at any traffic level.
- Coalescing (§11.4) is a write-time operation in the Celery flush task, not a read-time view. The raw intermediate states are intentionally discarded — they are not needed for recovery (§11.6 handles that) and bloat the table.
- The `audit:queue` Valkey key uses DB 1 (Celery broker DB, per `CLAUDE.md`). A dedicated DB 3 may be added if queue depth monitoring shows contention with Celery task dispatch — deferred to V1.5.
