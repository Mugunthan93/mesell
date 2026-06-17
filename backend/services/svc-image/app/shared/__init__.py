"""svc-image vendored shared foundation — config, database, valkey.

Trimmed copies of the monolith ``app.shared`` layer.  Settings carries ONLY
the env vars image needs (DATABASE_URL @schema ``image``, VALKEY_URL,
JWT_SECRET, GCS_*, GEMINI_* + LANGFUSE_* + AI budget for the vendored
watermark.v1 step, AUDIT_PII_SALT, APP_ENV + the monolith shim base URL) —
NO MSG91 / RAZORPAY / openpyxl.
"""
