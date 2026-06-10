"""Helpers for integration tests that need to introspect Set-Cookie headers.

Why we cannot rely on ``response.cookies``
------------------------------------------
The §7 iam refresh cookie is locked at ``Domain=.mesell.xyz`` per the §4.B
FE-D5 amendment.  httpx's cookie jar enforces RFC-style domain matching:
a cookie whose ``Domain`` attribute does not cover the request URL's host
(``testserver``) is silently DROPPED from ``response.cookies``.  The
ASGITransport-driven tests therefore see ``response.cookies`` as empty
even though the server emitted ``Set-Cookie: refresh_token=...; ...``.

These helpers parse the raw header instead, then propagate the token
explicitly via a ``Cookie:`` request header so the routes see the same
value the browser would have round-tripped.
"""

from __future__ import annotations

import re

from httpx import Response

_REFRESH_COOKIE_RE = re.compile(r"refresh_token=([^;]*)", re.IGNORECASE)


def extract_refresh_cookie(response: Response) -> str | None:
    """Return the ``refresh_token`` value from any ``Set-Cookie`` header.

    Returns ``None`` if no Set-Cookie header contained the cookie, OR if
    the cookie's value is empty (clear-cookie response — ``Max-Age=0``).
    """
    for header in response.headers.get_list("set-cookie"):
        m = _REFRESH_COOKIE_RE.search(header)
        if m:
            value = m.group(1)
            return value or None
    return None
