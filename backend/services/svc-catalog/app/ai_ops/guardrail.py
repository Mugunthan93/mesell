"""3-layer hallucination guardrail — Layers 1 & 2.  §6A.E.

Per philosophy M7 (AI works in canonical space) and ``MVP_ARCH §9.7``,
NO AI-emitted value that is not in the per-category enum allowlist
reaches the database OR the Export Adapter.  Defence-in-depth across
three layers:

* **Layer 1 (prompt-level)** — owned here.  A workload-specific prefix
  is prepended to every Gemini prompt instructing the model to obey
  shape/enum constraints.  The prefix is **bonded to the workload**,
  not to the prompt template, so it cannot be accidentally removed by
  a prompt-engineer template revision.

* **Layer 2 (parser-level)** — owned here.  After Gemini returns,
  :func:`parse_and_validate` parses the response text as JSON and
  checks every emitted enum value against the per-call allowlist.
  Returns ``None`` to signal a retry (consumer in
  :mod:`ai_ops.client` retries with a stricter prompt up to 2 times).

* **Layer 3 (export-time re-validation)** — owned by
  ``modules/export/service.py`` per §14 + ``MVP_ARCH §9.7``.  Even if
  Layers 1 + 2 are bypassed by a future bug, Layer 3 ensures no
  invalid enum reaches Meesho.

Workload contracts
------------------
* ``smart_picker`` — JSON shape ``{"suggestions": [{"category_id": str,
  "confidence": float, "reasons": list[str]}]}``.  No enum allowlist;
  Layer 2 validates shape only.  Confidence ∈ [0.0, 1.0].

* ``autofill`` — JSON shape ``{"fields": {<canonical_name>: <value>}}``.
  ``allowed_enums`` is a dict mapping canonical-field-name → list of
  allowed string values.  Layer 2 rejects any field whose emitted
  value is NOT in its allowlist (when allowlist is supplied).

* ``watermark`` — JSON shape ``{"has_watermark": bool, "confidence":
  float}``.  No enum allowlist; Layer 2 validates shape only.
  Confidence ∈ [0.0, 1.0].
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.ai_ops.cost_tracker import Workload

logger = logging.getLogger(__name__)


# ── Layer 1 — workload prefixes (locked at module level) ───────────────────
# Per §6A.E: "the prefix is bonded to the workload, not to the prompt
# template (so it cannot be accidentally removed when prompt-engineer
# ships a new template version)."
_LAYER1_PREFIX: dict[Workload, str] = {
    "smart_picker": (
        "You are a strict JSON generator.  Return STRICTLY one JSON object "
        "with the shape "
        '{"suggestions": [{"category_id": "...", "confidence": 0.0, '
        '"reasons": ["..."]}]}.  '
        "Return the top-5 ranked suggestions only.  "
        "Each confidence MUST be a float between 0.0 and 1.0.  "
        "DO NOT include markdown, prose, or explanation outside the JSON.\n\n"
    ),
    "autofill": (
        "You are a strict JSON generator.  Return STRICTLY one JSON object "
        'with the shape {"fields": {<canonical_field_name>: <value>}}.  '
        "You MUST select values ONLY from the allowed enum list provided "
        "for each field — NEVER generate a value that is not in the list. "
        "For free-text fields (no allowlist supplied), return your best "
        "value as a string.  "
        "DO NOT include markdown, prose, or explanation outside the JSON.\n\n"
    ),
    "watermark": (
        "You are a strict JSON generator.  Return STRICTLY one JSON object "
        'with the shape {"has_watermark": true|false, "confidence": 0.0}. '
        "Confidence MUST be a float between 0.0 and 1.0.  "
        "DO NOT include markdown, prose, or explanation outside the JSON.\n\n"
    ),
}


def apply_prompt_constraint(
    prompt: str,
    workload: Workload,
    allowed_enums: dict[str, list[str]] | None = None,
) -> str:
    """Layer 1 — prepend the workload-specific JSON-shape prefix.

    When ``workload == "autofill"`` AND ``allowed_enums`` is supplied,
    appends the enum allowlist after the locked prefix so the model
    sees the per-field constraints.

    Per §6A.E.

    Args:
        prompt: Caller's prompt body (the template-rendered output of
            :func:`ai_ops.prompt_registry.resolve`).
        workload: The 3-workload literal.
        allowed_enums: Optional per-field allowlist; ignored for
            ``smart_picker`` and ``watermark``.

    Returns:
        Prompt with the Layer 1 prefix prepended.
    """
    prefix = _LAYER1_PREFIX[workload]
    if workload == "autofill" and allowed_enums:
        prefix = prefix + "Allowed enums per field:\n" + _format_enum_block(
            allowed_enums
        ) + "\n\n"
    return prefix + prompt


def _format_enum_block(allowed_enums: dict[str, list[str]]) -> str:
    """Human-readable enum block for autofill's Layer 1 prefix."""
    return "\n".join(
        f"  - {field}: {sorted(values)}" for field, values in sorted(allowed_enums.items())
    )


# ── Layer 2 — parser-level validation ──────────────────────────────────────
def parse_and_validate(
    response_text: str,
    workload: Workload,
    allowed_enums: dict[str, list[str]] | None = None,
) -> dict[str, Any] | None:
    """Layer 2 — parse JSON and check shape + enum compliance.

    Returns the parsed dict on success.  Returns ``None`` on any
    validation failure (signals retry to
    :func:`ai_ops.client.call_gemini`).  Logs the violation at WARNING
    when returning ``None`` so observability surfaces drift.

    Per §6A.E.

    Args:
        response_text: Raw text from
            :class:`adapters.gemini.GeminiResponse.text`.
        workload: The 3-workload literal.
        allowed_enums: Per-field allowlist; required for ``autofill``
            with enum-constrained fields.

    Returns:
        Parsed dict if valid; ``None`` if invalid.
    """
    try:
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning(
            "ai_ops guardrail Layer 2: JSON parse failed (workload=%s): %r",
            workload,
            exc,
        )
        return None

    if not isinstance(parsed, dict):
        logger.warning(
            "ai_ops guardrail Layer 2: top-level not a dict (workload=%s, "
            "got %s)",
            workload,
            type(parsed).__name__,
        )
        return None

    if workload == "smart_picker":
        return _validate_smart_picker_shape(parsed)
    if workload == "autofill":
        return _validate_autofill_shape(parsed, allowed_enums or {})
    if workload == "watermark":
        return _validate_watermark_shape(parsed)
    # Unreachable per the Literal typing, but defend.
    logger.warning("ai_ops guardrail Layer 2: unknown workload %s", workload)
    return None


def _validate_smart_picker_shape(parsed: dict[str, Any]) -> dict[str, Any] | None:
    """``{"suggestions": [{category_id, confidence, reasons}]}`` shape."""
    suggestions = parsed.get("suggestions")
    if not isinstance(suggestions, list):
        logger.warning(
            "ai_ops guardrail Layer 2 smart_picker: missing/invalid 'suggestions'"
        )
        return None
    for i, sug in enumerate(suggestions):
        if not isinstance(sug, dict):
            logger.warning(
                "ai_ops guardrail Layer 2 smart_picker: suggestion %d not a dict", i
            )
            return None
        if not isinstance(sug.get("category_id"), str):
            logger.warning(
                "ai_ops guardrail Layer 2 smart_picker: suggestion %d "
                "missing/invalid category_id",
                i,
            )
            return None
        confidence = sug.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            logger.warning(
                "ai_ops guardrail Layer 2 smart_picker: suggestion %d "
                "confidence out of [0,1] (got %r)",
                i,
                confidence,
            )
            return None
        reasons = sug.get("reasons")
        if not isinstance(reasons, list) or not all(
            isinstance(r, str) for r in reasons
        ):
            logger.warning(
                "ai_ops guardrail Layer 2 smart_picker: suggestion %d "
                "reasons not list[str]",
                i,
            )
            return None
    return parsed


def _validate_autofill_shape(
    parsed: dict[str, Any], allowed_enums: dict[str, list[str]]
) -> dict[str, Any] | None:
    """``{"fields": {canonical_name: value}}`` shape + enum allowlist."""
    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        logger.warning(
            "ai_ops guardrail Layer 2 autofill: missing/invalid 'fields'"
        )
        return None
    for field_name, value in fields.items():
        if not isinstance(field_name, str):
            logger.warning(
                "ai_ops guardrail Layer 2 autofill: non-str field key %r", field_name
            )
            return None
        # If the field has an allowlist, value MUST be a string in the
        # allowlist.  If not in the allowlist, this is the M7 violation
        # we MUST catch.
        if field_name in allowed_enums:
            allowed = allowed_enums[field_name]
            if not isinstance(value, str) or value not in allowed:
                logger.warning(
                    "ai_ops guardrail Layer 2 autofill: field %s value %r "
                    "not in allowlist %r",
                    field_name,
                    value,
                    allowed,
                )
                return None
        else:
            # Free-text field — accept any JSON-serialisable scalar.
            if not isinstance(value, (str, int, float, bool)) and value is not None:
                logger.warning(
                    "ai_ops guardrail Layer 2 autofill: field %s value %r "
                    "not a scalar",
                    field_name,
                    value,
                )
                return None
    return parsed


def _validate_watermark_shape(parsed: dict[str, Any]) -> dict[str, Any] | None:
    """``{"has_watermark": bool, "confidence": float}`` shape."""
    has = parsed.get("has_watermark")
    if not isinstance(has, bool):
        logger.warning(
            "ai_ops guardrail Layer 2 watermark: has_watermark not bool (got %r)",
            has,
        )
        return None
    conf = parsed.get("confidence")
    if not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0:
        logger.warning(
            "ai_ops guardrail Layer 2 watermark: confidence out of [0,1] (got %r)",
            conf,
        )
        return None
    return parsed


def build_retry_prompt(
    original_rendered_prompt: str,
    workload: Workload,
    last_response_text: str,
    allowed_enums: dict[str, list[str]] | None,
) -> str:
    """Build a stricter prompt for the Layer 2 retry path.

    The retry escalates the constraint language and names the violation
    seen in ``last_response_text``.  Per §6A.E ("retry with a stricter
    prompt that names the violation").

    The returned prompt is fed back through
    :func:`apply_prompt_constraint` by the caller, so this body excludes
    the Layer 1 prefix.
    """
    return (
        "PREVIOUS ATTEMPT FAILED VALIDATION.  Your last response was:\n"
        f"  {last_response_text[:500]}\n"
        "Reasons for failure: it did not conform to the strict JSON shape "
        f"OR (for autofill) emitted a value outside the allowed enums.\n"
        "DO NOT repeat the same mistake.  Re-read the constraints carefully "
        "and emit ONLY the strict JSON.\n\n"
        + original_rendered_prompt
    )


__all__ = [
    "apply_prompt_constraint",
    "build_retry_prompt",
    "parse_and_validate",
]
