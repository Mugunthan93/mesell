"""``image`` internal domain types — frozen dataclasses per §11.G.

Per BACKEND_ARCHITECTURE.md §11.G (LOCKED 2026-06-05).

EXTRACTION NOTE (MS Sub-Plan C — spec §1 B1)
============================================
Vendored verbatim from the monolith ``app.modules.image.domain``.  No
intra-``app`` imports (stdlib only) so ZERO import-line changes were needed.

These types never cross the HTTP boundary directly — the Pydantic
schemas in :mod:`.schemas` are the wire shapes.  Using ``frozen=True``
+ ``kw_only=True`` keeps them immutable and safer to pass between
service-layer helpers.

Cross-module exports (consumed via ``from app.modules.image import
domain as image_domain``):

* :class:`ImageUrl`            — catalog.service.get_preview per §10.B.4
* :class:`ImageStatusSummary`  — dashboard.service.summary per §13
* :class:`PrecheckResult`      — internal; tasks.py assembles then
                                 service.write_precheck_result persists

Conversion between ORM ↔ domain happens at the repository boundary
(:mod:`.repository`).  Routers never see ORM instances; they map domain
objects to the Pydantic response shapes in :mod:`.schemas`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

ImageStatus = Literal["pending", "ready", "failed_precheck"]
"""§11.G locked status enum — see also ``product_images.status`` per
`MVP_ARCH §2.5` (which permits ``deleted`` as the V1 soft-delete marker
per §11-IMAGE-D1 deviation; see :func:`.repository.soft_delete_by_idx`)."""


WatermarkCheckOutcome = Literal[
    "no_watermark",
    "has_watermark",
    "uncertain",
    "skipped_budget",
]
"""§6A.F locked outcome enum for the watermark step.

``skipped_budget`` is the graceful-fallback marker — see §11.J + §6A.F
(when ``BudgetExceededError`` fires inside the Celery task, the
watermark check is non-blocking; overall status still resolves to
``"ready"`` if steps 1-4 pass)."""


@dataclass(frozen=True, kw_only=True)
class ProductImage:
    """Mirrors a ``product_images`` row per `MVP_ARCH §2.5`.

    ``user_id`` is denormalised onto the domain object even though
    the SQL row carries only ``product_id`` — the repository joins
    through ``products`` to populate the field.  Downstream consumers
    can rely on ``user_id`` for tenancy assertions without re-joining.

    ``is_front`` is the ``GENERATED ALWAYS AS (order_idx == 1) STORED``
    column — never settable from application code.
    """

    id: UUID
    product_id: UUID
    user_id: UUID
    gcs_path: str
    order_idx: int  # 1-4 per `MVP_ARCH §0` premise #3
    is_front: bool  # GENERATED ALWAYS AS (order_idx == 1) STORED
    width: int | None
    height: int | None
    color_space: str | None
    precheck_jsonb: dict
    status: str  # ``ImageStatus`` literal + V1 "deleted" sentinel — see D1
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class ImageUrl:
    """Cross-module return type for ``catalog.service.get_preview`` per
    §10.B.4 + §2.D matrix.

    Carries the 1-hour signed GCS URL + slot metadata.  Returned ONLY
    for ``status == 'ready'`` images by
    :func:`.service.get_image_urls`.

    ``__str__`` returns the bare ``signed_url`` so catalog's defensive
    integration (``tuple(str(u) for u in urls)`` per §10.service line
    ~830) yields URL strings — see §11-IMAGE-D3 deviation note in the
    service module.  Consumers that want the structured shape should
    read ``.signed_url`` / ``.is_front`` etc. explicitly.
    """

    image_id: UUID
    idx: int
    signed_url: str
    is_front: bool

    def __str__(self) -> str:  # noqa: D401 — backward-compat shim for §10 preview
        return self.signed_url


@dataclass(frozen=True, kw_only=True)
class ImageStatusSummary:
    """Cross-module return type for ``dashboard.service.summary`` per
    §13 + §2.D matrix.

    Aggregation: per-product image counts by status + the front-image
    signed URL (when slot 1 is ready).  Used by dashboard cards to
    render quick health indicators.
    """

    product_id: UUID
    total_images: int  # 0-4
    ready_count: int
    failed_count: int
    pending_count: int
    front_image_signed_url: str | None  # only when idx=1 is ``"ready"``


@dataclass(frozen=True, kw_only=True)
class PrecheckResult:
    """Internal — Celery task assembles this then writes the equivalent
    JSON shape to ``precheck_jsonb`` via
    :func:`.service.write_precheck_result` per §11.E step 7-8.

    The 5 keys map 1:1 onto ``precheck_jsonb``:

    * ``jpeg_valid``        — boolean (Pillow open succeeded as JPEG)
    * ``color_space``       — RGB / CMYK / Gray
    * ``resolution_pass``   — boolean (>= 1500x1500)
    * ``white_background``  — boolean (corner-sampling heuristic; V1)
    * ``watermark_check``   — ``WatermarkCheckOutcome``
    * ``watermark_confidence`` — float in [0,1] or None on skipped

    Overall image status resolves to ``"ready"`` iff steps 1-4
    (the deterministic Pillow checks) all pass.  Step 5 (watermark)
    is INFORMATIONAL only per §11.J + §6A.F.
    """

    jpeg_valid: bool
    color_space: Literal["RGB", "CMYK", "Gray"]
    resolution_pass: bool
    white_background: bool
    watermark_check: WatermarkCheckOutcome
    watermark_confidence: float | None

    def to_jsonb(self) -> dict:
        """Serialise to the `MVP_ARCH §2.5` ``precheck_jsonb`` shape.

        Returns a plain dict (JSON-serialisable) — values are primitives.
        Used by :mod:`.tasks` before calling
        :func:`.service.write_precheck_result`.
        """
        return {
            "jpeg_valid": bool(self.jpeg_valid),
            "color_space": str(self.color_space),
            "resolution_pass": bool(self.resolution_pass),
            "white_background": bool(self.white_background),
            "watermark_check": str(self.watermark_check),
            "watermark_confidence": (
                float(self.watermark_confidence)
                if self.watermark_confidence is not None
                else None
            ),
        }

    @property
    def deterministic_checks_pass(self) -> bool:
        """True iff the 4 Pillow-based deterministic steps all pass.

        The watermark step (step 5) is intentionally NOT included —
        it is informational, not blocking, per §11.J + §6A.F.
        """
        return (
            self.jpeg_valid
            and self.color_space == "RGB"
            and self.resolution_pass
            and self.white_background
        )


__all__ = [
    "ImageStatus",
    "ImageStatusSummary",
    "ImageUrl",
    "PrecheckResult",
    "ProductImage",
    "WatermarkCheckOutcome",
]
