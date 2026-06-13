"""svc-dashboard vendored shared foundation — config, database, valkey.

Trimmed copies of the monolith ``app.shared`` layer.  Settings carries ONLY
the env vars dashboard needs (DATABASE_URL — shared-session / get_db wiring
only, dashboard owns NO schema; VALKEY_URL; JWT_SECRET;
FEATURE_TRACKING_DASHBOARD_ENABLED; APP_ENV) — NO GEMINI / LANGFUSE / MSG91 /
RAZORPAY / GCS.  The DB pool is tiny (dashboard is a thin read-through view
that delegates all data access to its catalog + customer HTTP shims).
"""
