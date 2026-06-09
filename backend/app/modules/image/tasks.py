"""``image`` Celery tasks — 5-step precheck pipeline wrapper per §11.E.

Per BACKEND_ARCHITECTURE.md §11.E (LOCKED 2026-06-05).

Owned ENTIRELY by ``meesell-image-precheck-builder`` (AI track) per
§2.5 — the backend's ``image`` module owns the dispatch / wrapper
(this file), the AI track owns the pipeline algorithm internals
(the 5 step functions below).

§11.E locked 9-step flow
------------------------
1. Fetch image bytes from GCS via
   :func:`adapters.gcs.download_bytes(path=image.gcs_path)`.
2. Step 1: JPEG check (Pillow open) — fail → ``jpeg_valid=False`` +
   status=``"failed_precheck"`` (early exit).
3. Step 2: RGB vs CMYK check (Pillow mode) — flag CMYK as
   non-compliant.
4. Step 3: Resolution ≥ 1500x1500 check.
5. Step 4: White-background heuristic (Pillow corner-sampling V1).
6. Step 5: Watermark vision via
   ``ai_ops.client.call_gemini(ctx, "watermark.v1", {}, image_bytes=...)``.
   Layer 2 guardrail validates ``{"has_watermark", "confidence"}``
   shape per §6A.E.  On ``BudgetExceededError`` →
   ``precheck_jsonb.watermark_check = "skipped_budget"`` per §6A.F
   graceful fallback (informational, non-blocking — status still
   resolves to ``"ready"`` if steps 1-4 pass).
7. Aggregate into ``precheck_jsonb``; set status=``"ready"`` if all 4
   deterministic steps pass — watermark step is informational, not
   blocking — else ``"failed_precheck"``.
8. Call :func:`image.service.write_precheck_result` to persist.
9. Worker JWT re-validation per §1.G — the task payload carries
   ``user_id``; the worker re-validates by checking the user exists
   in ``users`` (the access JWT itself has expired by the time this
   task runs).

Direct audit write
------------------
Emits ``image.precheck.completed`` event to ``audit_events`` via the
same documented-exception pattern as §6A.D ``cost_tracker`` and §7
``verify_otp`` — the worker has no request-close hook so
``audit_mw`` cannot fire.

Synchronous task
----------------
``@shared_task`` (not ``async def``) because Celery's runtime does
not support coroutines in V1.  Async work inside the task body uses
``asyncio.run(...)`` for the GCS download + Gemini call + DB write.
The ``bind=True`` decorator exposes ``self`` for retry semantics.

DECISION FLAG §11-IMAGE-D4 (informational)
------------------------------------------
``call_gemini`` already catches ``BudgetExceededError`` internally
and returns the fallback envelope per §6A client.py implementation.
We additionally wrap the call in a defensive ``try/except`` so
external mocks (per §11.K integration test #2 contract) that raise
``BudgetExceededError`` directly are also handled.  Belt-and-suspenders
— the production path goes through the client's internal handler.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError

from app.adapters import GcsAdapterError
from app.shared.config import settings  # noqa: F401 — kept for downstream env lookups
from app.shared.database import AsyncSessionLocal
from app.shared.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 5-step precheck pipeline — owned by meesell-image-precheck-builder (AI track)
# ─────────────────────────────────────────────────────────────────────────────
def _check_jpeg(data: bytes) -> tuple[bool, Any]:
    """Step 1 — JPEG validity (Pillow open + format inspection).

    Returns ``(jpeg_valid, pillow_image_or_None)``.  The Pillow Image
    object is returned so subsequent steps can re-use it without a
    second open.
    """
    from io import BytesIO

    from PIL import Image, UnidentifiedImageError

    try:
        img = Image.open(BytesIO(data))
        img.load()  # forces a header parse
        is_jpeg = (img.format or "").upper() in ("JPEG", "JPG")
        return is_jpeg, img if is_jpeg else None
    except (UnidentifiedImageError, OSError, ValueError):
        return False, None


def _check_color_space(img: Any) -> str:
    """Step 2 — color space (Pillow ``Image.mode``).

    Returns ``"RGB"`` | ``"CMYK"`` | ``"Gray"`` per §11.G
    ``PrecheckResult`` contract.  Mapping rule:

    * ``"RGB"`` / ``"RGBA"`` → ``"RGB"``
    * ``"CMYK"``             → ``"CMYK"``
    * ``"L"`` / ``"LA"``     → ``"Gray"``
    * other (palette / etc.) → ``"Gray"`` (treated as non-compliant)
    """
    mode = (img.mode or "").upper()
    if mode in ("RGB", "RGBA"):
        return "RGB"
    if mode == "CMYK":
        return "CMYK"
    if mode in ("L", "LA"):
        return "Gray"
    return "Gray"  # defensive — anything unknown is treated as non-RGB


def _check_resolution(img: Any) -> bool:
    """Step 3 — minimum resolution ≥ 1500x1500 per `MVP_ARCH §5.3`."""
    width, height = img.size
    return width >= 1500 and height >= 1500


def _check_white_background(img: Any) -> bool:
    """Step 4 — corner-sampling white-background heuristic (V1 simple).

    Samples the 4 corners (5x5 pixel patches) and returns ``True`` iff
    the average per-channel brightness exceeds 235/255 in all 4 corners.
    Tolerates compression artefacts (the 235 threshold is the V1
    setting; the AI-track precheck-builder may tune during the §19
    golden eval pass).

    Operates on the in-memory Pillow image — no GCS roundtrip.
    """
    if img.mode not in ("RGB", "RGBA"):
        # Force RGB for the sampling — CMYK / palette images may give
        # misleading brightness; convert defensively.
        try:
            img = img.convert("RGB")
        except (OSError, ValueError):
            return False

    width, height = img.size
    if width < 10 or height < 10:
        return False

    # 5x5 sample regions at each corner.
    regions = (
        (0, 0, 5, 5),
        (width - 5, 0, width, 5),
        (0, height - 5, 5, height),
        (width - 5, height - 5, width, height),
    )

    threshold = 235  # 0..255
    for box in regions:
        try:
            patch = img.crop(box)
        except (OSError, ValueError):
            return False
        pixels = list(patch.getdata())
        if not pixels:
            return False
        # Average per-channel — only the first 3 channels matter (RGB).
        sample_avg_r = sum(p[0] for p in pixels) / len(pixels)
        sample_avg_g = sum(p[1] for p in pixels) / len(pixels)
        sample_avg_b = sum(p[2] for p in pixels) / len(pixels)
        if sample_avg_r < threshold or sample_avg_g < threshold or sample_avg_b < threshold:
            return False
    return True


async def _check_watermark(
    image_bytes: bytes,
    user_id: UUID,
) -> tuple[str, float | None]:
    """Step 5 — watermark vision via ai_ops.client.call_gemini.

    Returns ``(watermark_check, confidence)`` where ``watermark_check``
    is one of ``"no_watermark"``, ``"has_watermark"``, ``"uncertain"``,
    ``"skipped_budget"`` per :class:`PrecheckResult` enum.

    Behaviour:

    * ``call_gemini`` already catches ``BudgetExceededError`` internally
      per §6A and returns the fallback envelope.  We additionally wrap
      with defensive ``try/except`` for the §11.K test fixture that
      injects ``BudgetExceededError`` directly via mock.
    * Layer 2 retry exhaustion → ``"uncertain"``.
    * Adapter failure → ``"uncertain"``.
    """
    # Lazy imports — heavy and Celery-specific.
    from app.ai_ops import budget_cap, client as ai_client

    ctx = ai_client.AICallContext(
        workload="watermark",
        user_id=user_id,
    )

    try:
        response = await ai_client.call_gemini(
            ctx,
            prompt_id="watermark.v1",
            prompt_vars={},
            image_bytes=image_bytes,
        )
    except budget_cap.BudgetExceededError:
        # Test-fixture path — production call_gemini handles this internally.
        return "skipped_budget", None
    except Exception as exc:  # noqa: BLE001 — adapter / vendor failure
        logger.warning("watermark vision call failed (user=%s): %r", user_id, exc)
        return "uncertain", None

    parsed = response.parsed
    if not isinstance(parsed, dict):
        return "uncertain", None

    # Fallback envelope — budget exhausted internally (or guardrail).
    fallback_marker = parsed.get("watermark_check")
    if fallback_marker == "skipped_budget":
        return "skipped_budget", None
    if fallback_marker == "skipped_guardrail":
        return "uncertain", None

    # Normal Gemini path — {"has_watermark": bool, "confidence": float}.
    if "has_watermark" not in parsed:
        return "uncertain", None

    has_wm = parsed.get("has_watermark")
    if has_wm is None:
        # has_watermark explicitly null in the response (rare; treat as uncertain).
        return "uncertain", None

    confidence_raw = parsed.get("confidence")
    try:
        confidence = float(confidence_raw) if confidence_raw is not None else None
    except (TypeError, ValueError):
        confidence = None

    outcome = "has_watermark" if bool(has_wm) else "no_watermark"
    return outcome, confidence


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline aggregator (sync — runs inside the Celery task body via asyncio.run)
# ─────────────────────────────────────────────────────────────────────────────
async def _run_precheck_pipeline(
    image_id: UUID,
    user_id: UUID,
) -> tuple[dict, str]:
    """End-to-end async pipeline runner.

    Returns ``(precheck_jsonb_dict, final_status)`` where
    ``final_status`` is ``"ready"`` or ``"failed_precheck"`` per §11.E
    step 7.

    Side effects:

    * Persists the result via
      :func:`image.service.write_precheck_result`.
    * Emits ``image.precheck.completed`` audit row.
    """
    from app.adapters import gcs as gcs_adapter
    from app.modules.image import repository as image_repo
    from app.modules.image import service as image_service

    # 1. Resolve the image — get its GCS path + sanity-check tenancy.
    async with AsyncSessionLocal() as session:
        image_row = await image_repo.find_by_id(session, user_id, image_id)
    if image_row is None:
        logger.warning(
            "precheck_task: image %s not found under user %s — skipping",
            image_id,
            user_id,
        )
        return {}, "failed_precheck"

    # 2-5. Download + run 5-step pipeline.
    try:
        image_bytes = await gcs_adapter.download_bytes(path=image_row.gcs_path)
    except GcsAdapterError as exc:
        logger.warning(
            "precheck_task: GCS download failed (%s): %r", image_row.gcs_path, exc
        )
        # Retry semantics handled by @shared_task autoretry_for=(AdapterError,);
        # raise so Celery picks it up.
        raise

    jpeg_valid, pillow_img = _check_jpeg(image_bytes)
    if not jpeg_valid or pillow_img is None:
        # Early exit — but still record the failure with 5 keys per §11.K
        # int_001 acceptance: ``precheck_jsonb`` has 5 keys regardless of
        # which step failed.
        precheck_jsonb = {
            "jpeg_valid": False,
            "color_space": "Gray",
            "resolution_pass": False,
            "white_background": False,
            "watermark_check": "uncertain",
            "watermark_confidence": None,
        }
        async with AsyncSessionLocal() as session:
            await image_service.write_precheck_result(
                image_id,
                user_id,
                precheck_jsonb,
                "failed_precheck",
                db=session,
            )
            await session.commit()
        await _emit_precheck_completed_audit(
            user_id=user_id,
            image_id=image_id,
            precheck_jsonb=precheck_jsonb,
            final_status="failed_precheck",
        )
        return precheck_jsonb, "failed_precheck"

    color_space = _check_color_space(pillow_img)
    resolution_pass = _check_resolution(pillow_img)
    white_background = _check_white_background(pillow_img)
    watermark_check, watermark_confidence = await _check_watermark(image_bytes, user_id)

    deterministic_pass = (
        jpeg_valid
        and color_space == "RGB"
        and resolution_pass
        and white_background
    )
    final_status = "ready" if deterministic_pass else "failed_precheck"

    precheck_jsonb = {
        "jpeg_valid": bool(jpeg_valid),
        "color_space": str(color_space),
        "resolution_pass": bool(resolution_pass),
        "white_background": bool(white_background),
        "watermark_check": str(watermark_check),
        "watermark_confidence": (
            float(watermark_confidence) if watermark_confidence is not None else None
        ),
    }

    # 6. Persist via service surface.
    async with AsyncSessionLocal() as session:
        await image_service.write_precheck_result(
            image_id,
            user_id,
            precheck_jsonb,
            final_status,
            db=session,
        )
        await session.commit()

    # 7. Direct audit write.
    await _emit_precheck_completed_audit(
        user_id=user_id,
        image_id=image_id,
        precheck_jsonb=precheck_jsonb,
        final_status=final_status,
    )

    return precheck_jsonb, final_status


async def _emit_precheck_completed_audit(
    *,
    user_id: UUID,
    image_id: UUID,
    precheck_jsonb: dict,
    final_status: str,
) -> None:
    """Direct ORM write to ``audit_events`` for ``image.precheck.completed``.

    Same documented-exception pattern as §6A.D ``cost_tracker._write_audit_row``
    and §7 ``verify_otp`` — the worker has no request-close hook, so the
    standard ``audit_mw`` post-commit path cannot fire.

    Drops on failure with a warning log — audit observability MUST NOT
    block the precheck pipeline per the §1.E lock.
    """
    try:
        async with AsyncSessionLocal() as session:
            row = AuditEvent(
                user_id=user_id,
                event_type="image.precheck.completed",
                entity_type="product_image",
                entity_id=image_id,
                diff_jsonb=None,
                metadata_jsonb={
                    "precheck_jsonb": dict(precheck_jsonb),
                    "final_status": str(final_status),
                    "emitted_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            session.add(row)
            await session.commit()
    except (SQLAlchemyError, Exception) as exc:  # noqa: BLE001 — informational
        logger.warning(
            "image.precheck.completed audit_events write failed "
            "(user=%s image=%s): %r",
            user_id,
            image_id,
            exc,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Celery task entrypoint
# ─────────────────────────────────────────────────────────────────────────────
@shared_task(
    name="image.precheck",
    bind=True,
    max_retries=2,
    retry_backoff=True,
)
def image_precheck_task(self, image_id: str | UUID, user_id: str | UUID) -> dict:
    """§11.E — Celery task wrapper for the 5-step precheck pipeline.

    Synchronous Celery task; the async pipeline runs inside via
    ``asyncio.run(...)``.  Returns the assembled ``precheck_jsonb`` +
    ``final_status`` dict so callers / monitors can read the result
    from the Celery result backend (Valkey DB 2).

    Args:
        image_id: ``product_images.id`` UUID (or its string form).
        user_id:  Owning user's UUID (or its string form).

    Retry policy (per ``@shared_task`` decorator):

    * ``max_retries=2`` — total 3 attempts.
    * ``retry_backoff=True`` — exponential backoff.
    * Transient ``GcsAdapterError`` from ``download_bytes`` propagates;
      Celery retries automatically.
    """
    # Coerce string-form UUIDs (Celery JSON serialiser strips UUID type).
    image_uuid = image_id if isinstance(image_id, UUID) else UUID(str(image_id))
    user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))

    try:
        precheck_jsonb, final_status = asyncio.run(
            _run_precheck_pipeline(image_uuid, user_uuid)
        )
    except GcsAdapterError as exc:
        logger.warning(
            "image.precheck retry (image=%s): GCS adapter failure: %r",
            image_uuid,
            exc,
        )
        raise self.retry(exc=exc) from exc

    return {
        "image_id": str(image_uuid),
        "user_id": str(user_uuid),
        "status": final_status,
        "precheck_jsonb": precheck_jsonb,
    }


__all__ = [
    "image_precheck_task",
]
