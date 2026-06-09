"""i18n message-id resolver — §5A.I locked contract.

The single import surface every error/exception path uses to translate a
``validation_message_id`` (per §5A.H 3-segment convention) into a
human-readable string for the active locale.

Fallback order (LOCKED per §5A.I item 1–3):

    1. requested ``locale`` (V1 ships only ``"en"``; V1.5 lights ``"ta"`` /
       ``"hi"`` per §3.H placeholders).
    2. ``"en"`` (the canonical fallback locale — every key MUST exist here).
    3. the ``message_id`` itself, returned verbatim. This is the
       "debug-hint" tier: it surfaces seed/registry gaps to the dev tier
       without breaking the response envelope. §6A/§19 observability
       counts these as ``i18n.resolver.missing_key`` increments.

V1 behaviour: the ``locale`` parameter is accepted, logged, and
short-circuited to ``"en"`` immediately (§5A.I item 4 — V1 logs the
``Accept-Language`` header but always returns English). V1.5 swaps the
short-circuit for a real locale-dispatch table.

This module deliberately has zero side-effects at import time besides
loading the English registry, so it is safe to import from
``core/errors.py`` at startup (no test fixture monkeypatching surface
required).
"""

from __future__ import annotations

import logging
from typing import Final

from app.core.metrics import I18N_MISSING_KEY
from app.i18n.messages_en import VALIDATION_MESSAGES as _MESSAGES_EN

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Locale → registry table
# V1: only "en". V1.5 will add "ta" and "hi" by importing
# ``app.i18n.messages_ta`` / ``app.i18n.messages_hi`` and registering them
# here. The fallback order in :func:`resolve` consults this table by
# requested-locale-then-en.
# ----------------------------------------------------------------------------
_REGISTRIES: Final[dict[str, dict[str, str]]] = {
    "en": _MESSAGES_EN,
}

# Sentinel for missing-key observability. Tests assert on this string
# value as a stable contract.
_VERBATIM_SENTINEL_LOG = "i18n.resolver.missing_key"


def resolve(message_id: str, locale: str = "en") -> str:
    """Resolve a ``validation_message_id`` to a localised display string.

    Args:
        message_id: The 3-segment snake_case ID per §5A.H, e.g.
            ``"validation.product_name.too_short"``. Not validated against
            the regex at runtime — that is the §19 CI Contract 10
            registry-time check. A caller passing a non-conforming ID
            will still get a verbatim return (last-resort tier).
        locale: One of the registered locale codes. V1 honours only
            ``"en"``; any other value falls through to the English
            registry per §5A.I item 4. Defaults to ``"en"``.

    Returns:
        The human-readable string for ``(locale, message_id)``. Fallback
        order locked per §5A.I:
          1. requested ``locale`` registry
          2. ``"en"`` registry
          3. ``message_id`` verbatim (debug hint; logs at WARNING with
             the ``i18n.resolver.missing_key`` discriminator so §6A/§19
             observability can count it).
    """
    # Step 1 — try requested locale.
    registry = _REGISTRIES.get(locale)
    if registry is not None:
        hit = registry.get(message_id)
        if hit is not None:
            return hit
        # Locale registered but key missing — fall through to en.
        if locale != "en":
            logger.debug(
                "i18n: %s missing in locale=%s; falling back to en",
                message_id,
                locale,
            )

    # Step 2 — fall back to English.
    en_hit = _REGISTRIES["en"].get(message_id)
    if en_hit is not None:
        return en_hit

    # Step 3 — verbatim ID. Log at WARNING + bump the §15.J Prometheus counter
    # so observability picks up the seed/registry gap.
    I18N_MISSING_KEY.labels(message_id=message_id).inc()
    logger.warning(
        "%s: message_id=%s locale=%s",
        _VERBATIM_SENTINEL_LOG,
        message_id,
        locale,
    )
    return message_id


__all__ = ["resolve"]
