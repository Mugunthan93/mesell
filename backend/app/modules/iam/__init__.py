"""``iam`` — Identity & Access Management module.

Owner specialist: ``meesell-auth-builder`` (per §2.1 + §4.B sole-owner lock).

Per BACKEND_ARCHITECTURE.md §7 (LOCKED 2026-06-05), this module exposes
6 endpoint surfaces:

1. ``POST /api/v1/auth/otp/send``      — Feature 1 phone OTP send
2. ``POST /api/v1/auth/otp/verify``    — Feature 1 phone OTP verify + JWT issue
3. ``POST /api/v1/auth/refresh``       — FE-D5 silent refresh
4. ``POST /api/v1/auth/logout``        — FE-D5 server-side revocation
5. ``GET  /api/v1/auth/me``            — JWT introspection (infra surface)
6. ``POST /api/v1/webhooks/razorpay``  — V1 capture-only webhook

The public router lives in :mod:`.router`; the service surface lives in
:mod:`.service`; the repository (module-private per §16) lives in
:mod:`.repository`.
"""

from app.modules.iam.router import router as iam_router

__all__ = ["iam_router"]
