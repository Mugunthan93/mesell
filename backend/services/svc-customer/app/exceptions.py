"""``customer`` module exceptions — subclasses of
:class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §8.G (LOCKED 2026-06-05) + the §8 sub-session
master ruling 5 (2026-06-07) on 3-segment validation_message_ids.

Validation-message-id convention (§5A.H locked regex)::

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

Six customer-specific IDs land in ``app/i18n/messages_en.py`` per §5A.I
(strings already present from the §5A construction):

============================================  =======  ==========================================
Class                                         status   validation_message_id
============================================  =======  ==========================================
CustomerError (base)                          —        — (inherits MeesellError defaults)
ProfileNotFoundError                          404      customer.profile.not_found
InvalidPincodeError                           422      validation.pincode.invalid_format
InvalidSuperCategoryError                     422      validation.super_category.unknown
SuperCategoryNotDeclaredError                 404      customer.super_category.not_declared
ComplianceExtensionMissingFieldsError         422      customer.compliance.missing_fields
ProfileIncompleteForCategoryError             422      customer.profile.incomplete_for_category
============================================  =======  ==========================================

Note: §8.G prose lists 6 subclass IDs.  ``InvalidPincodeError`` is normally
fired by Pydantic's ``Field(pattern=r"^\\d{6}$")`` regex producing a 422
envelope via :class:`app.core.errors._pydantic_validation_handler`.  This
subclass exists for defensive service-layer raises (e.g. compliance
extension payloads carrying their own pincode value, which sit outside the
Pydantic schema's regex check) and to keep the 6-message-ID inventory
complete.
"""

from __future__ import annotations

from app.core.errors import MeesellError


class CustomerError(MeesellError):
    """Base class for ``customer`` module failures. Never raised directly."""

    code = "customer.base"


class ProfileNotFoundError(CustomerError):
    """Raised when a caller looks up a profile that has not been created yet.

    Per §8.B.1 mapping: 404 / ``customer.profile.not_found``.  The frontend
    interprets this as "first-time seller" and redirects to the onboarding
    wizard.

    Also raised by ``customer.service.get_profile`` (the cross-module
    variant called by ``catalog`` / ``export`` / ``dashboard`` when they
    REQUIRE a profile to exist).  ``get_profile_or_none`` is the read-only
    variant that returns ``None`` instead.
    """

    code = "customer.profile_not_found"
    status_code = 404
    validation_message_id = "customer.profile.not_found"

    def __init__(self, detail: str = "Seller profile not found.") -> None:
        super().__init__(detail=detail)


class InvalidPincodeError(CustomerError):
    """Raised when a pincode fails the locked ``^\\d{6}$`` Indian regex.

    Per §8.E + §8.B.2 mapping: 422 / ``validation.pincode.invalid_format``.
    Pydantic normally fires this via the schema's ``Field(pattern=...)``
    constraint — this subclass exists for defensive service-layer raises.
    """

    code = "customer.invalid_pincode"
    status_code = 422
    validation_message_id = "validation.pincode.invalid_format"

    def __init__(self, detail: str = "Pincode must be 6 digits.") -> None:
        super().__init__(detail=detail)


class InvalidSuperCategoryError(CustomerError):
    """Raised when an unknown ``super_id`` is presented to
    ``set_active_categories``.

    Per §8.B.3 mapping: 422 / ``validation.super_category.unknown``.  The
    valid set is the distinct ``super_id`` column of the ``categories``
    table (cached read via :mod:`app.core.cache`).
    """

    code = "customer.invalid_super_category"
    status_code = 422
    validation_message_id = "validation.super_category.unknown"

    def __init__(
        self,
        detail: str = "One or more category groups are not recognised.",
        unknown_super_ids: list[str] | None = None,
    ) -> None:
        super().__init__(detail=detail)
        self.unknown_super_ids = unknown_super_ids or []


class SuperCategoryNotDeclaredError(CustomerError):
    """Raised when ``set_compliance_extension`` targets a ``super_id`` that
    is NOT in ``active_super_categories``.

    Per §8.B.4 mapping: 404 / ``customer.super_category.not_declared``.
    Distinct from :class:`InvalidSuperCategoryError` — the ``super_id``
    may be perfectly valid in the global registry; it just hasn't been
    declared by THIS seller yet.
    """

    code = "customer.super_category_not_declared"
    status_code = 404
    validation_message_id = "customer.super_category.not_declared"

    def __init__(
        self,
        detail: str = "You have not declared this category group on your profile.",
        super_id: str | None = None,
    ) -> None:
        super().__init__(detail=detail)
        self.super_id = super_id


class ComplianceExtensionMissingFieldsError(CustomerError):
    """Raised when the compliance extension payload is missing required keys
    per :data:`domain.COMPLIANCE_EXTENSION_MAP`.

    Per §8.B.4 mapping: 422 / ``customer.compliance.missing_fields``.  The
    envelope payload lists which keys are missing — the frontend renders
    inline form errors against those names.

    Attribute ``missing_keys`` carries the offending list for routes /
    audit middleware to surface in logs (no PII — just the field names).
    """

    code = "customer.compliance_missing_fields"
    status_code = 422
    validation_message_id = "customer.compliance.missing_fields"

    def __init__(
        self,
        detail: str = "Some compliance fields are missing for this category.",
        super_id: str | None = None,
        missing_keys: list[str] | None = None,
    ) -> None:
        super().__init__(detail=detail)
        self.super_id = super_id
        self.missing_keys = missing_keys or []


class ProfileIncompleteForCategoryError(CustomerError):
    """Raised by ``customer.service.assert_eligible_for_super_id`` from the
    catalog cross-module path (``catalog.service.create_product``).

    Per §8.B + §10 PROFILE_INCOMPLETE_FOR_CATEGORY gate (per
    ``MVP_ARCH §3.3``).  Eligibility = profile exists AND ``super_id`` in
    ``active_super_categories`` AND all required compliance extension
    keys for the ``super_id`` are present.

    Status 422 / ``customer.profile.incomplete_for_category``.  The
    frontend interprets this as "send the seller back to onboarding to
    complete the missing block".
    """

    code = "customer.profile_incomplete_for_category"
    status_code = 422
    validation_message_id = "customer.profile.incomplete_for_category"

    def __init__(
        self,
        detail: str = (
            "Your seller profile is incomplete for this category. "
            "Please update your profile to list here."
        ),
        super_id: str | None = None,
        missing_keys: list[str] | None = None,
    ) -> None:
        super().__init__(detail=detail)
        self.super_id = super_id
        self.missing_keys = missing_keys or []


__all__ = [
    "ComplianceExtensionMissingFieldsError",
    "CustomerError",
    "InvalidPincodeError",
    "InvalidSuperCategoryError",
    "ProfileIncompleteForCategoryError",
    "ProfileNotFoundError",
    "SuperCategoryNotDeclaredError",
]
