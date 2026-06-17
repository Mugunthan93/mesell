"""svc-export vendored shared foundation — config, database, valkey.

Trimmed copies of the monolith ``app.shared`` layer.  Settings carries
ONLY the env vars export needs (DATABASE_URL @schema ``export``,
VALKEY_URL, JWT_SECRET, GCS_*, APP_ENV + the monolith shim base URL) —
NO GEMINI / LANGFUSE / MSG91 / RAZORPAY.
"""
