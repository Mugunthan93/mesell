"""svc-dashboard i18n — vendored SUBSET of the monolith presentation contract.

Only the dashboard ``validation_message_id`` string
(``validation.dashboard.invalid_pagination``) + the cross-cutting IDs the
vendored error/tenancy/rate-limit/auth layers raise are carried here (spec
§3.A).  The full monolith registry (55 IDs across 8 domains) is NOT vendored —
svc-dashboard only ever emits the dashboard pagination envelope + a handful of
cross-cutting envelopes.
"""
