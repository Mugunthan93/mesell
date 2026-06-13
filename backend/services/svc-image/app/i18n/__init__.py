"""svc-image i18n — vendored SUBSET of the monolith presentation contract.

Only the image ``validation_message_id`` strings + the cross-cutting IDs the
vendored error/tenancy/rate-limit/auth/adapter + ai_ops layers raise are
carried here (spec §1 B1).  The full monolith registry (55 IDs across 8
domains) is NOT vendored — svc-image only ever emits image + a handful of
cross-cutting envelopes.
"""
