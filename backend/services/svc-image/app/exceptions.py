"""``image`` module exceptions — subclasses of
:class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §11.H (LOCKED 2026-06-05).

EXTRACTION NOTE (MS Sub-Plan C — spec §1 B1)
============================================
Vendored verbatim from the monolith ``app.modules.image.exceptions``.  The
single import (``from app.core.errors import MeesellError``) is at the same
flat path in the svc-image vendored ``core`` — ZERO import-line changes.

Validation-message-id convention (§5A.H locked regex)::

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

Five image-specific IDs ship in ``app/i18n/messages_en.py`` per §5A.I.

DECISION FLAG §11-IMAGE-D2 (applied — same precedent as §7/§8/§9/§10)
--------------------------------------------------------------------
§11.H prose lists ``image.slot_occupied`` / ``image.not_found`` as
2-segment shorthand.  The §5A.H regex locks 3-segment.
``app/i18n/messages_en.py`` ships the canonical 3-segment IDs
(``image.slot.occupied``, ``image.not.found``).  Wire to the canonical
3-segment IDs already registered.

============================================  =======  ==========================================
Class                                         status   validation_message_id
============================================  =======  ==========================================
ImageError (base)                             —        — (inherits MeesellError defaults)
InvalidImageFormatError                       400      validation.image.invalid_format
ImageTooLargeError                            400      validation.image.too_large
InvalidImageIdxError                          400      validation.image.invalid_idx
ImageSlotOccupiedError                        409      image.slot.occupied
ImageNotFoundError                            404      image.not.found
============================================  =======  ==========================================
"""

from __future__ import annotations

from app.core.errors import MeesellError


class ImageError(MeesellError):
    """Base class for ``image`` module failures.  Never raised directly."""

    code = "image.base"


class InvalidImageFormatError(ImageError):
    """Raised when an uploaded file is not a JPEG per §11.B.1 step 2.

    V1 accepts JPEG only.  Front-end clients MUST convert PNG / WEBP /
    HEIC to JPEG before upload — the §11.M ``DELETE-image`` deferral
    means a wrong-format upload occupies the slot until the product is
    deleted, so we reject early at MIME-type validation.
    """

    code = "image.invalid_format"
    status_code = 400
    validation_message_id = "validation.image.invalid_format"

    def __init__(self, detail: str = "Only JPEG images are accepted.") -> None:
        super().__init__(detail=detail)


class ImageTooLargeError(ImageError):
    """Raised when an upload exceeds 10 MB per CLAUDE.md API design rules
    + §11.B.1 step 2.

    The cap is enforced BEFORE the GCS write to avoid wasted bandwidth.
    """

    code = "image.too_large"
    status_code = 400
    validation_message_id = "validation.image.too_large"

    def __init__(self, detail: str = "Image exceeds the 10 MB upload limit.") -> None:
        super().__init__(detail=detail)


class InvalidImageIdxError(ImageError):
    """Raised when the ``idx`` form-field is not in ``[1, 2, 3, 4]`` per
    `MVP_ARCH §0` premise #3 (4-slot uniform corpus-wide).

    The DB-level ``CHECK (order_idx BETWEEN 1 AND 4)`` constraint per
    `MVP_ARCH §2.5` is the structural backstop; the route-level check
    fails fast with a seller-friendly message.
    """

    code = "image.invalid_idx"
    status_code = 400
    validation_message_id = "validation.image.invalid_idx"

    def __init__(self, detail: str = "Image slot must be between 1 and 4.") -> None:
        super().__init__(detail=detail)


class ImageSlotOccupiedError(ImageError):
    """Raised when the seller POSTs an image to a slot that already has
    a non-deleted row per §11.B.1 step 4.

    V1 does NOT expose a DELETE-image endpoint per §11.M — the only
    recourse is to soft-delete the parent product and re-create.
    """

    code = "image.slot_occupied"
    status_code = 409
    validation_message_id = "image.slot.occupied"

    def __init__(self, detail: str = "This image slot is already occupied.") -> None:
        super().__init__(detail=detail)


class ImageNotFoundError(ImageError):
    """Raised when ``image.service.get_image_bytes`` (or future lookups)
    cannot find an image owned by the caller.

    Same leak-protection rationale as
    :class:`catalog.exceptions.ProductNotFoundError`: non-existent vs
    cross-tenant vs soft-deleted all collapse to a single 404 envelope.
    """

    code = "image.not_found"
    status_code = 404
    validation_message_id = "image.not.found"

    def __init__(self, detail: str = "Image not found.") -> None:
        super().__init__(detail=detail)


__all__ = [
    "ImageError",
    "ImageNotFoundError",
    "ImageSlotOccupiedError",
    "ImageTooLargeError",
    "InvalidImageFormatError",
    "InvalidImageIdxError",
]
