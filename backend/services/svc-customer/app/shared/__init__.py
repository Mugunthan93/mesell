"""svc-customer vendored shared foundation — config, database, valkey.

Trimmed copies of the monolith ``app.shared`` layer.  Settings carries ONLY the
env vars customer needs (DATABASE_URL @ schema ``customer``; VALKEY_URL — DB 0
rate-limit/audit-coalesce + DB 3 read-through cache; JWT_SECRET; CACHE_VERSION;
APP_ENV; AUDIT_PII_SALT; CORS; MONOLITH_INTERNAL_BASE_URL for the outbound
category shim) — NO GEMINI / LANGFUSE / MSG91 / RAZORPAY / GCS.  NO Celery
broker / result-backend factories.
"""
