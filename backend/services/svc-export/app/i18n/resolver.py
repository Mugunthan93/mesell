"""svc-export i18n resolver — locale-aware message lookup.

Vendored from the monolith ``app.i18n.resolver`` (§5A.I).  V1 ships
English-only; the fallback chain is locale → en → verbatim ID.  When the
verbatim ID is returned (registry gap), the caller in ``core/errors``
substitutes the exception's draft prose.
"""

from __future__ import annotations

import logging

from app.i18n.messages_en import VALIDATION_MESSAGES

logger = logging.getLogger(__name__)

# V1 ships a single locale registry.  V1.5 widens this to a per-locale map.
_REGISTRIES: dict[str, dict[str, str]] = {"en": VALIDATION_MESSAGES}


def resolve(message_id: str, locale: str = "en") -> str:
    """Resolve ``message_id`` to a human string per §5A.I.

    Fallback chain: requested locale → ``en`` → verbatim ID.  Logs a
    WARNING when the verbatim ID is returned (registry-gap observability).
    """
    registry = _REGISTRIES.get(locale) or _REGISTRIES["en"]
    resolved = registry.get(message_id)
    if resolved is not None:
        return resolved
    en_resolved = _REGISTRIES["en"].get(message_id)
    if en_resolved is not None:
        return en_resolved
    logger.warning("i18n.resolver.missing_key: %s (locale=%s)", message_id, locale)
    return message_id


__all__ = ["resolve"]
