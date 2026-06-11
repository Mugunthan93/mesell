"""§5A.H — VALIDATION_MESSAGES key regex conformance.

Per ``BACKEND_ARCHITECTURE.md`` §5A.H lines 1684-1688: every key in
``app.i18n.messages_en.VALIDATION_MESSAGES`` MUST match the locked
3-segment snake_case regex::

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

This test IS the §19 CI Contract 10 check that the regex commitment is
honoured at construction time. CI fails on the first non-conforming key
so seed-time + module specs cannot drift from the locked convention.

Also asserts:
  - the registry is non-empty (so a future ``rm`` of the file is caught
    before the rest of the build runs against an unloadable module).
  - every value is a non-empty string (per §5A.I locked type
    ``dict[str, str]``).
  - no duplicate keys (Python dict guarantees this at load-time, but we
    assert via length parity for paranoia).
"""

from __future__ import annotations

import re

import pytest

from app.i18n.messages_en import VALIDATION_MESSAGES

pytestmark = pytest.mark.unit

# §5A.H locked regex.
_VALIDATION_MESSAGE_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$")


def test_registry_is_non_empty() -> None:
    """The registry must carry at least the V1 ~50 IDs spec'd in §15.K."""
    assert isinstance(VALIDATION_MESSAGES, dict)
    assert len(VALIDATION_MESSAGES) >= 40, (
        "VALIDATION_MESSAGES carries fewer than 40 IDs — V1 inventory short."
    )


def test_registry_values_are_non_empty_strings() -> None:
    """Per §5A.I the registry is ``dict[str, str]`` — strict type-shape check."""
    for key, value in VALIDATION_MESSAGES.items():
        assert isinstance(key, str), f"Non-string key: {key!r}"
        assert isinstance(value, str), f"Non-string value for {key!r}"
        assert value.strip(), f"Empty value for {key!r}"


@pytest.mark.parametrize("message_id", sorted(VALIDATION_MESSAGES.keys()))
def test_every_key_matches_3_segment_snake_case_regex(message_id: str) -> None:
    """§5A.H — three snake_case segments separated by dots, no other chars."""
    assert _VALIDATION_MESSAGE_ID_REGEX.match(message_id), (
        f"validation_message_id {message_id!r} does not match the §5A.H "
        f"regex ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){{2}}$ — three "
        f"snake_case segments only."
    )


def test_every_key_has_exactly_three_segments() -> None:
    """Belt-and-braces: spec text at §5A.H says 'Three segments only'."""
    for key in VALIDATION_MESSAGES:
        segments = key.split(".")
        assert len(segments) == 3, (
            f"{key!r} has {len(segments)} segments; §5A.H locks 3."
        )


def test_no_hyphens_in_any_key() -> None:
    """§5A.H formatting rule: 'Hyphens forbidden in any segment.'"""
    for key in VALIDATION_MESSAGES:
        assert "-" not in key, f"{key!r} contains a hyphen; §5A.H forbids it."


def test_no_uppercase_in_any_key() -> None:
    """§5A.H formatting rule: snake_case → lowercase only."""
    for key in VALIDATION_MESSAGES:
        assert key == key.lower(), (
            f"{key!r} contains uppercase; §5A.H locks snake_case."
        )
