"""Unit test §8.J #2 — pincode regex enforcement.

Per BACKEND_ARCHITECTURE.md §8.J unit 2:

    "Pincode regex enforcement — invalid pincodes (5 digits, 7 digits,
    alphanumeric) → 422 with ``validation_message_id =
    'validation.pincode.invalid_format'``."

Pydantic v2 fires the ValidationError at schema construction time when
the ``Field(pattern=r"^\\d{6}$")`` constraint fails.  The §4.F handler
chain then builds the locked envelope.  This test asserts at the schema
construction layer (the locked regex IS the contract); the route-level
envelope shape is asserted in the integration tests.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.customer.schemas import PatchProfileRequest


@pytest.mark.parametrize(
    "bad_pincode",
    [
        "12345",       # 5 digits
        "1234567",     # 7 digits
        "ABCDEF",      # alphanumeric
        "12345a",      # mixed
        "      ",      # whitespace
        " 123456",     # leading space
        "123456 ",     # trailing space
        "12-345",      # hyphen
    ],
    ids=[
        "5_digits",
        "7_digits",
        "alpha",
        "mixed_alpha",
        "all_whitespace",
        "leading_space",
        "trailing_space",
        "hyphen",
    ],
)
def test_manufacturer_pincode_rejects_invalid(bad_pincode: str):
    """Manufacturer pincode rejects every non-6-digit value."""
    with pytest.raises(ValidationError) as excinfo:
        PatchProfileRequest(manufacturer_pincode=bad_pincode)
    # At least one error must target the pincode field.
    errors = excinfo.value.errors()
    field_paths = [".".join(str(p) for p in e["loc"]) for e in errors]
    assert any("manufacturer_pincode" in p for p in field_paths), (
        f"Expected manufacturer_pincode in error locations; got {field_paths}"
    )


@pytest.mark.parametrize(
    "field_name",
    ["manufacturer_pincode", "packer_pincode", "importer_pincode"],
)
def test_all_three_pincodes_enforce_regex(field_name: str):
    """All 3 pincode fields enforce the same regex."""
    with pytest.raises(ValidationError):
        PatchProfileRequest(**{field_name: "BADCODE"})


def test_valid_pincode_passes():
    """6-digit pincode is accepted."""
    patch = PatchProfileRequest(manufacturer_pincode="560001")
    assert patch.manufacturer_pincode == "560001"


def test_none_pincode_passes():
    """None / unset pincode is accepted (partial PATCH semantics)."""
    patch = PatchProfileRequest()
    assert patch.manufacturer_pincode is None
    assert patch.packer_pincode is None
    assert patch.importer_pincode is None
