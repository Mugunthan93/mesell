"""image-svc HTTP shim — re-exports the ``image_service`` symbol surface.

Shims 1 of the 6 cross-module methods export consumes (spec §0.4):

* :func:`list_images` ← image/service.py:232
  → ``GET /internal/products/{id}/images`` (returns the ImagesListResponse
  shape — signed GCS URLs, 1 h TTL).

PLAN-TEXT CORRECTION (spec §0.4): the plan mis-named this shim
``get_image_bytes``.  Export NEVER calls ``get_image_bytes`` — it consumes
the image refs / signed-URL summaries from ``list_images`` (the
front-image-present gate in ``initiate_export`` reads ``img.idx`` + ``img.status``).

Matches the ``service.py`` call site
``list_images(user_id=user_id, product_id=product_id, db=db)`` (keyword args,
``db`` accepted + IGNORED — HTTP shim).

The deserialization targets (:class:`ImagesListResponse` / :class:`ImageSummary`)
mirror ``image/schemas.py:50-95`` field shape so the export gate's attribute
access (``payload.images`` → ``img.idx`` / ``img.status``) is identical to the
in-process version.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


# ── Deserialization targets (mirror image/schemas.py shapes) ────────────────
@dataclass(frozen=True)
class ImageSummary:
    """Mirror of ``image.schemas.ImageSummary`` (the subset the export gate
    reads — ``idx`` + ``status`` drive the front-image-present check; the rest
    are carried for completeness).
    """

    image_id: UUID
    idx: int
    status: str
    signed_url: str
    precheck_jsonb: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ImagesListResponse:
    """Mirror of ``image.schemas.ImagesListResponse`` — per-product list
    ordered by ``idx`` ASC, length 0-4.
    """

    images: list[ImageSummary] = field(default_factory=list)


# ── Shimmed method (re-export the image_service symbol surface) ─────────────
async def list_images(
    user_id: UUID,
    product_id: UUID,
    *,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> ImagesListResponse:
    """Image list ← ``GET /internal/products/{id}/images``.

    Deserializes the monolith JSON into :class:`ImagesListResponse`.  A 404 (or
    any error) is left to propagate — the only export caller wraps this in the
    ``xlsx_with_images`` front-image gate, where a missing product surfaces as
    the broader pipeline failure (consistent with the in-process behaviour).
    """
    from app.core.extracted_clients._transport import request_json

    payload = await request_json(
        "GET",
        f"/internal/products/{product_id}/images",
        params={"user_id": str(user_id)},
    )

    raw_images = payload.get("images") or []
    images: list[ImageSummary] = []
    for item in raw_images:
        if not isinstance(item, dict):
            continue
        images.append(
            ImageSummary(
                image_id=UUID(str(item["image_id"])),
                idx=int(item["idx"]),
                status=str(item["status"]),
                signed_url=str(item.get("signed_url", "")),
                precheck_jsonb=dict(item.get("precheck_jsonb") or {}),
            )
        )
    return ImagesListResponse(images=images)


__all__ = [
    "ImageSummary",
    "ImagesListResponse",
    "list_images",
]
