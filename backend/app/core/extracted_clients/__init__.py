"""Monolith-side reverse shims for extracted microservices (MS program).

This package holds the MONOLITH's HTTP client shims that re-export the public
service symbol surface of an extracted service so that — AT CUTOVER — an
in-monolith caller can swap

    from app.modules.<callee> import service as <callee>_service

for

    from app.core.extracted_clients import <callee>_client as <callee>_service

with ZERO change to the call sites (§16.G byte-for-byte contract).

MS-3 (Sub-Plan E — customer extraction) introduces the FIRST such reverse
shim: :mod:`customer_client`.  The monolith ``catalog.service`` is the caller
(``assert_eligible_for_super_id`` + ``get_compliance_block``).

STRANGLER POSTURE (NOT cut over by this PR)
-------------------------------------------
This package is built + hybrid-CI-tested but the live import at
``catalog/service.py`` is NOT flipped and the in-process ``customer_router``
mount in ``main.py`` is NOT removed.  Both the in-process customer module and
the extracted customer-svc run in parallel until the founder-gated cutover
(separate PR, after the 7-day green window).  See
``docs/runbooks/customer-svc-rollback.md``.
"""
