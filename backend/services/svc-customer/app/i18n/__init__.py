"""svc-customer i18n — vendored SUBSET of the monolith presentation contract.

Carries the customer module-specific ``validation_message_id`` strings (§8.G +
the 10 base-field ``validation_message_ids`` referenced in
``service._BASE_FIELD_DEFINITIONS``) + the cross-cutting IDs the vendored
error / tenancy / rate-limit / auth core layers raise (spec §3.A).  The full
monolith registry (55 IDs across 8 domains) is NOT vendored — svc-customer only
ever emits the customer envelopes + a handful of cross-cutting envelopes.
"""
