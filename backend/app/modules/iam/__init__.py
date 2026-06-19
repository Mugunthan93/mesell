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
7. ``POST /api/v1/auth/google/verify`` — google-auth feature (flag-gated;
   mounted via ``google_router`` only when FEATURE_GOOGLE_AUTH_ENABLED)

Razorpay Wave 3 adds the billing router (4 endpoints):

8. ``POST /api/v1/billing/subscribe``   — Start subscription / LTD purchase
9. ``POST /api/v1/billing/start-trial`` — Start 14-day app-side Pro trial
10.``POST /api/v1/billing/cancel``      — Cancel subscription at cycle end
11.``GET  /api/v1/billing/subscription``— Current billing/plan/trial status

The billing router is mounted separately (``iam_billing_router``) in ``main.py``
and is gated on ``FEATURE_BILLING_ENABLED``, mirroring the google-auth pattern.

The public router lives in :mod:`.router`; the billing router in
:mod:`.billing_router`; the service surface in :mod:`.service`; the repository
(module-private per §16) lives in :mod:`.repository`.
"""

from app.modules.iam.billing_router import billing_router as iam_billing_router
from app.modules.iam.router import google_router as iam_google_router
from app.modules.iam.router import router as iam_router

__all__ = ["iam_router", "iam_google_router", "iam_billing_router"]
