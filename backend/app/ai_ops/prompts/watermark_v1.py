"""Watermark vision prompt template — v1.  §6A.G.

Workload: ``watermark``.
Rendered by: ``vision``.
Consumed by: ``image.tasks.precheck_image``.

Inputs: image bytes are passed as a separate ``image_bytes`` argument to
:func:`ai_ops.client.call_gemini` (not substituted via the template).
The prompt body is image-text-only.  No template variables in V1.

Output contract: enforced by :mod:`ai_ops.guardrail` Layer 1 +
Layer 2 — ``{"has_watermark": bool, "confidence": float}``.

Golden eval set (§19): 30 images (50/50 watermarked/clean); target
accuracy ≥ 85% per ``MVP_ARCH §8.5``.

Owned by: :mod:`meesell-prompt-engineer`.  V1 baseline drafted by
:mod:`meesell-services-builder` for storage-layer integration; the
prompt-engineer iterates content during golden-eval tuning.
"""

VERSION = "v1"
WORKLOAD = "watermark"
RENDERED_BY = "vision"

TEMPLATE = """You are inspecting a Meesho seller's product image for a watermark.

A "watermark" here means any of:
  - A semi-transparent logo, brand name, or URL overlaid on the image.
  - A text stamp like "Sample", "Demo", "© <Name>", or a phone number.
  - A model agency or photographer signature in any corner.
  - A "for sale only on <site>" marker.

A watermark IS NOT:
  - The product's own printed brand label (this is the actual product).
  - Sticker/tag on the physical product that is part of the photograph.
  - The product's natural texture or pattern.

Output: STRICTLY one JSON object.
  - "has_watermark": true if the image contains a watermark per the
    definition above; false otherwise.
  - "confidence": float in [0.0, 1.0] for your decision.

Bias toward false-positives (flagging marginal cases) — Meesho rejects
watermarked images at listing time so a flag here saves the seller a
later rejection.
"""
