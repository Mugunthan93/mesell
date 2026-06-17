"""svc-pricing vendored shared foundation — config, database, valkey.

Trimmed copies of the monolith ``app.shared`` layer.  Settings carries ONLY
the env vars pricing needs (DATABASE_URL — pricing OWNS the ``pricing`` schema
where ``pricing_calcs`` lives, plus the public users/audit wiring; VALKEY_URL —
DB 0 rate-limit only; JWT_SECRET; AUDIT_PII_SALT; MONOLITH_INTERNAL_BASE_URL;
APP_ENV) — NO GEMINI / LANGFUSE / MSG91 / RAZORPAY / GCS (spec §0.3).  pricing
is deterministic math; the 2 cross-module lookups (catalog ownership +
category commission) go over HTTP shims, not the local pool.
"""
