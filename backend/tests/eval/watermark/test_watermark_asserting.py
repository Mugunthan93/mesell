"""QA Wave 3 — W3-BE-10: Watermark detection asserting eval.

Strengthens ``run_watermark_eval.py`` (a manual runner with a sys.exit
non-pytest interface) into an asserting pytest test that:

  - Asserts that watermarked fixtures flag True from ``detect_watermark``.
  - Asserts that clean fixtures flag False from ``detect_watermark``.
  - Asserts the overall accuracy is >= 85% (26/30 correct).

The ``detect_watermark`` function is imported from the existing
``run_watermark_eval`` module (the rule-set lives there — do NOT copy it).
Fixture data is read from ``fixtures.json`` co-located in this directory.

No real Gemini call is made. The eval is entirely based on the structured
signal metadata in fixtures.json (token-free, deterministic).

Marker: eval (golden-fixture eval; no network, no DB, no GCS).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.ai_eval

_HERE = Path(__file__).resolve().parent
_FIXTURES_PATH = _HERE / "fixtures.json"
_THRESHOLD_PCT = 85.0


def _load_fixtures() -> list[dict]:
    data = json.loads(_FIXTURES_PATH.read_text())
    assert isinstance(data, list), "watermark fixtures.json must be a JSON list"
    return data


# Import the rule set from the existing runner (do not duplicate).
# If the import fails (module not importable from pytest context), the test is
# collected as an error — which is intentional: the fixture + runner must co-exist.
from tests.eval.watermark.run_watermark_eval import detect_watermark  # noqa: E402


_FIXTURES = _load_fixtures()
_WATERMARKED = [f for f in _FIXTURES if f["expected_has_watermark"]]
_CLEAN = [f for f in _FIXTURES if not f["expected_has_watermark"]]


# ─────────────────────────────────────────────────────────────────────────────
# Fixture-count sanity
# ─────────────────────────────────────────────────────────────────────────────

def test_watermark_fixture_count():
    """Exactly 30 fixtures must be present (>=26/30 for 85% accuracy contract)."""
    assert len(_FIXTURES) == 30, (
        f"Expected 30 watermark fixtures, got {len(_FIXTURES)}"
    )


def test_watermark_fixture_split():
    """Fixtures must be balanced: at least 10 watermarked AND at least 10 clean."""
    assert len(_WATERMARKED) >= 10, (
        f"Expected >= 10 watermarked fixtures; got {len(_WATERMARKED)}"
    )
    assert len(_CLEAN) >= 10, (
        f"Expected >= 10 clean fixtures; got {len(_CLEAN)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Parametrized: each watermarked fixture must be flagged True
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "fixture",
    _WATERMARKED,
    ids=[f["id"] for f in _WATERMARKED],
)
def test_watermarked_fixture_is_flagged(fixture: dict) -> None:
    """detect_watermark(signals) must return True for each watermarked fixture.

    Arrange: load the structured signals dict from the fixture.
    Act: call detect_watermark.
    Assert: result is True (the image carries a watermark).
    """
    predicted = detect_watermark(fixture["signals"])
    assert predicted is True, (
        f"[{fixture['id']}] Expected has_watermark=True for watermarked image; "
        f"got False. Description: {fixture['description'][:80]!r}. "
        f"Signals: {fixture['signals']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Parametrized: each clean fixture must NOT be flagged
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "fixture",
    _CLEAN,
    ids=[f["id"] for f in _CLEAN],
)
def test_clean_fixture_is_not_flagged(fixture: dict) -> None:
    """detect_watermark(signals) must return False for each clean fixture.

    Arrange: load the structured signals dict from the fixture.
    Act: call detect_watermark.
    Assert: result is False (the image does NOT carry a watermark).
    """
    predicted = detect_watermark(fixture["signals"])
    assert predicted is False, (
        f"[{fixture['id']}] Expected has_watermark=False for clean image; "
        f"got True. Description: {fixture['description'][:80]!r}. "
        f"Signals: {fixture['signals']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Overall accuracy assertion (≥ 85%)
# ─────────────────────────────────────────────────────────────────────────────

def test_overall_watermark_accuracy_meets_threshold() -> None:
    """Overall accuracy across all 30 fixtures must be >= 85%.

    This is the contract from §22.C / V1_FEATURE_SPEC Feature 5.
    The parametrized per-fixture tests above catch individual failures;
    this test enforces the numeric contract.
    """
    passed = 0
    failures: list[str] = []

    for fixture in _FIXTURES:
        expected = bool(fixture["expected_has_watermark"])
        predicted = detect_watermark(fixture["signals"])
        if predicted == expected:
            passed += 1
        else:
            failures.append(
                f"  [{fixture['id']}] predicted={predicted} expected={expected} "
                f"-- {fixture['description'][:60]!r}"
            )

    total = len(_FIXTURES)
    accuracy_pct = round(100.0 * passed / total, 1) if total else 0.0

    assert accuracy_pct >= _THRESHOLD_PCT, (
        f"Watermark accuracy {accuracy_pct}% < {_THRESHOLD_PCT}% threshold "
        f"({passed}/{total} correct). Failures:\n" + "\n".join(failures)
    )
