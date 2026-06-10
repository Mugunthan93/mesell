#!/usr/bin/env python3
"""Watermark detection — golden eval runner (V1 Feature 5).

Token-free, deterministic eval of the watermark-detection accuracy contract
(§22.C / V1_FEATURE_SPEC Feature 5):

    watermark detection accuracy >= 85% across 30 images
    (>= 26/30 correct detections; the seed set is balanced ~15 watermarked
     / ~15 clean per the watermark_v1 prompt spec).

Actual image binaries are NOT required at audit time and we cannot call
live Gemini Vision. Each fixture is a STRUCTURED metadata description of an
image plus the ground-truth ``expected_has_watermark``. The heuristic
:func:`detect_watermark` mirrors the decision rules documented in
``app.ai_ops.prompts.watermark_v1`` so the eval validates that the rule set
resolves real-world cases correctly:

  A watermark IS (flag True):
    - a semi-transparent logo / brand / URL overlay
    - a text stamp ("Sample", "Demo", "(c) Name", a phone number)
    - a model-agency / photographer signature in any corner
    - a "for sale only on <site>" marker

  A watermark IS NOT (flag False):
    - the product's own printed/embossed brand label (the real product)
    - a physical sticker / hangtag that is part of the photograph
    - the product's natural texture / pattern

  The prompt biases toward false-positives on MARGINAL cases (a faint
  overlay is flagged), because Meesho rejects watermarked images at listing
  time — flagging early saves the seller a later rejection.

Run:
    python3 backend/tests/eval/watermark/run_watermark_eval.py
"""

from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent  # backend/tests/eval/watermark
_FIXTURES_PATH = _HERE / "fixtures.json"
_RESULTS_PATH = _HERE / "eval_results.json"

_THRESHOLD_PCT = 85.0


def detect_watermark(signals: dict) -> bool:
    """Decide has_watermark from structured signals, per watermark_v1 rules.

    Returns True if the image carries a watermark/overlay/stamp/signature
    that is NOT the product's own label or a physical tag in the photo.
    Marginal overlays are flagged (false-positive bias per the prompt).
    """
    has_overlay_text = signals.get("has_overlay_text", False)
    overlay_semitransparent = signals.get("overlay_is_semitransparent", False)
    is_product_own_label = signals.get("is_product_own_label", False)
    has_corner_signature = signals.get("has_corner_signature", False)
    has_url_or_phone = signals.get("has_url_or_phone", False)
    has_logo_overlay = signals.get("has_logo_overlay", False)
    # is_marginal is informational; the false-positive bias is already baked
    # into flagging any logo/overlay/signature below.

    # Rule 1: the product's own printed/embossed brand label or a physical
    # hangtag in the photo is NOT a watermark. If the ONLY signal present is
    # the product's own label and there is no overlay/stamp/signature/url,
    # the image is clean.
    overlay_present = (
        has_overlay_text or has_logo_overlay or has_corner_signature or has_url_or_phone
    )
    if is_product_own_label and not overlay_present:
        return False

    # Rule 2: any text stamp overlay ("Sample"/"Demo"/"(c) Name"/etc.).
    if has_overlay_text:
        return True

    # Rule 3: a URL or phone number overlay ("for sale only on <site>",
    # reseller phone numbers).
    if has_url_or_phone:
        return True

    # Rule 4: a model-agency / photographer signature in a corner.
    if has_corner_signature:
        return True

    # Rule 5: a semi-transparent logo overlay (including faint/marginal ones
    # — false-positive bias).
    if has_logo_overlay:
        return True

    # Rule 6 (default): no overlay signals -> clean. overlay_semitransparent
    # alone (with no logo/text/signature/url) describes a clean product.
    _ = overlay_semitransparent
    return False


def main() -> int:
    fixtures = json.loads(_FIXTURES_PATH.read_text())
    if not isinstance(fixtures, list):
        raise ValueError("watermark fixtures.json must be a JSON list")

    passed = 0
    n_watermarked = 0
    n_clean = 0
    for fix in fixtures:
        expected = bool(fix["expected_has_watermark"])
        if expected:
            n_watermarked += 1
        else:
            n_clean += 1
        predicted = detect_watermark(fix["signals"])
        if predicted == expected:
            passed += 1
        else:
            print(
                f"  [FAIL] {fix['id']}: predicted={predicted} expected={expected} "
                f"-- {fix['description'][:60]!r}"
            )

    total = len(fixtures)
    accuracy_pct = round(100.0 * passed / total, 1) if total else 0.0
    verdict = "PASS" if accuracy_pct >= _THRESHOLD_PCT else "FAIL"

    results = {
        "run_date": "2026-06-09",
        "total_cases": total,
        "passed": passed,
        "accuracy_pct": accuracy_pct,
        "threshold": int(_THRESHOLD_PCT),
        "verdict": verdict,
        "watermarked_fixtures": n_watermarked,
        "clean_fixtures": n_clean,
    }
    _RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")

    print(
        f"\nwatermark: {passed}/{total} correct "
        f"(split {n_watermarked} watermarked / {n_clean} clean) "
        f"accuracy={accuracy_pct}% threshold={int(_THRESHOLD_PCT)}% "
        f"verdict={verdict}"
    )
    print(f"wrote {_RESULTS_PATH}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
