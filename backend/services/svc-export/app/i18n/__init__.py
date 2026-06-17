"""svc-export i18n — vendored SUBSET of the monolith presentation contract.

Only the export ``validation_message_id`` strings + the cross-cutting IDs
the vendored error/tenancy/rate-limit layers raise are carried here (spec
§3.A).  The full monolith registry (55 IDs across 8 domains) is NOT
vendored — svc-export only ever emits export + a handful of cross-cutting
envelopes.
"""
