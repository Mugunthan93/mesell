"""svc-iam — standalone identity / OTP / token-issuance microservice (MS Sub-Plan G).

Extracted from the monolith ``app.modules.iam`` (BACKEND_ARCHITECTURE.md §7
LOCKED 2026-06-05) per the validated MS extraction recipe.  The business logic
(``service.py`` / ``repository.py`` / ``domain.py`` / ``exceptions.py``) is
vendored byte-for-byte under the §16.G discipline.

iam is ALL-✗ on the cross-module call graph (SUB_PLAN_0G §0.4): it makes ZERO
outbound cross-module calls and exposes ZERO inbound ``/internal/*`` routes.
Its contract to every other service is the vendored ``core/auth.py``
(``get_current_user`` + JWT verify + the issuance / rotation primitives) plus
the shared ``JWT_SECRET`` (A2 / D7 — every service validates JWTs LOCALLY).
iam is the ONLY service that also runs the issuance / rotation half of
``core/auth.py`` from a route.

Owns the ``users`` table exclusively, bound to the ``iam`` Postgres schema
(moved ``public`` → ``iam`` in MS-4 Phase A, migration ``b1c2d3e4f5a6``; the 6
cross-schema FKs to ``users.id`` were dropped — §0.7).

NO AI track, NO storage, NO Celery (iam has no ``tasks.py`` — §0.2).  The FE-D5
cookie / dual-pepper allowlist / Lua rotation contract is LIVE and FROZEN.

The package root re-exports nothing at import time — ``main.py`` mounts the
router import-tolerantly so the app boots before ``router.py`` (delivered by
meesell-api-routes-builder, Phase B) lands.  ``service.py`` + ``core/auth.py``
are delivered by meesell-auth-builder on the SAME branch AFTER this
services-builder scaffold.
"""
