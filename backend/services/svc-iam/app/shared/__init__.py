"""svc-iam vendored shared foundation — config, database, valkey.

Trimmed copies of the monolith ``app.shared`` layer.  Settings carries ONLY
the env vars iam needs (DATABASE_URL — iam OWNS the ``iam`` schema where
``users`` lives, plus the public audit wiring; VALKEY_URL — DB 0 only, for OTP
records + the FE-D5 refresh-allowlist + rate-limit windows; JWT_SECRET +
ACCESS/REFRESH TTLs + the dual-pepper REFRESH_TOKEN_PEPPER* trio; MSG91_* for
OTP send; RAZORPAY_* for the webhook HMAC; AUDIT_PII_SALT; CORS_*; APP_ENV) —
NO GEMINI / LANGFUSE / GCS (iam has no AI / storage) and NO
MONOLITH_INTERNAL_BASE_URL (iam is all-✗ in the call matrix — no outbound HTTP
shims).  ``valkey.py`` keeps the DB 0 factory + the Lua ``load_lua_script`` /
``eval_lua_script`` helpers (used by the vendored ``core/auth.py`` refresh
rotation), but NOT the Celery broker / result-backend factories.
"""
