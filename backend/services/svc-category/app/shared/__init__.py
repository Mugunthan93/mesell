"""svc-category vendored shared foundation — config, database, valkey, models.

Trimmed copies of the monolith ``app.shared`` layer.  Settings carries ONLY
the env vars category needs (DATABASE_URL @schema ``category``, VALKEY_URL,
JWT_SECRET, GEMINI_* + LANGFUSE_* + AI budget for the vendored smart_picker.v1
step, AUDIT_PII_SALT, CACHE_VERSION, FEATURE_SMART_PICKER_ENABLED, APP_ENV) —
NO MSG91 / RAZORPAY / GCS / openpyxl / celery.  The 5 ORM models bind 3 tables
to the ``category`` schema + audit_event/user to ``public``.
"""
