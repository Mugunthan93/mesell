"""svc-iam i18n — vendored SUBSET of the monolith presentation contract.

Only the iam ``validation_message_id`` strings (the 8 iam exception IDs + the 3
``core/auth.py`` auth-dependency IDs) + the 3 cross-cutting IDs the vendored
error / tenancy / plan_guard layers raise are carried here (SUB_PLAN_0G
§"Code surfaces").  The full monolith registry (55 IDs across 8 domains) is NOT
vendored — svc-iam only ever emits the iam envelopes + a handful of
cross-cutting envelopes.
"""
