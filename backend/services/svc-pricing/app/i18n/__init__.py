"""svc-pricing i18n — vendored SUBSET of the monolith presentation contract.

Only the 5 pricing ``validation_message_id`` strings (the 2 exception IDs +
the 3 alert IDs) + the cross-cutting IDs the vendored
error/tenancy/rate-limit/auth layers raise are carried here (spec §3.A).  The
full monolith registry (55 IDs across 8 domains) is NOT vendored — svc-pricing
only ever emits the pricing envelopes + a handful of cross-cutting envelopes.
"""
