"""D2 Gate 2 — 20-image deterministic precheck smoke (4 Pillow checks only).

Per ``docs/plans/features/image-precheck/FEATURE_PLAN.md`` Gate 2 (§977-991):

    All 10 known-bad images -> ``status="failed_precheck"``;
    all 10 known-good images -> ``status="ready"``;
    per-image total Pillow time <= 2 seconds.

This is the CONSUMER-side smoke of the 4 DETERMINISTIC checks owned by
``app.modules.image.tasks`` (``_check_jpeg`` / ``_check_color_space`` /
``_check_resolution`` / ``_check_white_background``). The functions under test
are IMPORTED, never re-implemented — if a check is wrong, the fix belongs in
``tasks.py`` (and is escalated to the AI lead), not here.

Watermark (Step 5, Gemini Vision) is OUT OF SCOPE for this smoke (FEATURE_PLAN
§999) — no live Gemini, no GEMINI_API_KEY use, no network. The aggregation rule
asserted here is the AS-BUILT deterministic gate:

    status == "ready"  iff  jpeg AND color_space == "RGB"
                            AND resolution AND white_background

The image is opened EXACTLY ONCE per fixture: ``_check_jpeg`` performs the
single ``Image.open(BytesIO(...))`` and returns the in-memory Pillow image,
which is then reused by the other three checks — never four separate opens
(latency budget).

Regenerate fixtures with::

    python3 backend/tests/eval/precheck_smoke/gen_fixtures.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

# ── Env bootstrap (mirror conftest.py L13-19) ────────────────────────────────
# Importing ``app.modules.image.tasks`` transitively loads
# ``app.shared.config.Settings`` which fail-fasts on missing §5.D env vars.
# These are DUMMY non-secret placeholders so the import succeeds hermetically
# in CI / laptop runs. NEVER a real GEMINI_API_KEY — the watermark step is not
# exercised here and no network call is made.
_DUMMY_ENV = {
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+asyncpg://meesell:password@localhost:5432/meesell",
    "VALKEY_URL": "redis://localhost:6381/15",
    "JWT_SECRET": "test-secret-do-not-use",
    "REFRESH_TOKEN_PEPPER": "test-pepper-do-not-use",
    "MSG91_AUTH_KEY": "test",
    "MSG91_TEMPLATE_ID": "test",
    "RAZORPAY_KEY_ID": "test",
    "RAZORPAY_KEY_SECRET": "test",
    "RAZORPAY_WEBHOOK_SECRET": "test",
    "GEMINI_API_KEY": "test-not-a-real-key",
    "GCS_BUCKET": "test-bucket",
    "GCS_PROJECT_ID": "test-project",
    "LANGFUSE_PUBLIC_KEY": "test",
    "LANGFUSE_SECRET_KEY": "test",
    "AUDIT_PII_SALT": "test-salt",
    "CORS_ALLOWED_ORIGINS": "https://app.meesell.test",
}
for _k, _v in _DUMMY_ENV.items():
    os.environ.setdefault(_k, _v)

# Import the AS-BUILT deterministic checks — DO NOT re-implement.
from app.modules.image.tasks import (  # noqa: E402
    _check_color_space,
    _check_jpeg,
    _check_resolution,
    _check_white_background,
)

_HERE = Path(__file__).resolve().parent
_FIXTURES_JSON = _HERE / "fixtures.json"

# Per-image Pillow budget (Gate 2 acceptance): the 4 deterministic checks
# complete in <= 2 seconds per image.
_PILLOW_BUDGET_SECONDS = 2.0


def _load_fixtures() -> list[dict]:
    data = json.loads(_FIXTURES_JSON.read_text())
    assert isinstance(data, list), "fixtures.json must be a JSON list"
    return data


def _run_deterministic_checks(image_bytes: bytes) -> tuple[dict, str, float]:
    """Run the 4 deterministic checks with a SINGLE image open.

    Returns ``(results, status, elapsed_seconds)`` where ``status`` applies
    the AS-BUILT aggregation rule.
    """
    start = time.monotonic()

    # Step 1 — the ONLY Image.open happens inside _check_jpeg; it returns the
    # in-memory image for reuse by steps 2-4 (no second open).
    jpeg_valid, img = _check_jpeg(image_bytes)

    if jpeg_valid and img is not None:
        color_space = _check_color_space(img)
        resolution_pass = _check_resolution(img)
        white_background = _check_white_background(img)
    else:
        # Early-exit shape mirrors tasks.py: a non-JPEG never reaches steps 2-4.
        color_space = "Gray"
        resolution_pass = False
        white_background = False

    elapsed = time.monotonic() - start

    deterministic_pass = (
        jpeg_valid
        and color_space == "RGB"
        and resolution_pass
        and white_background
    )
    status = "ready" if deterministic_pass else "failed_precheck"

    results = {
        "jpeg_valid": jpeg_valid,
        "color_space": color_space,
        "resolution_pass": resolution_pass,
        "white_background": white_background,
    }
    return results, status, elapsed


_FIXTURES = _load_fixtures()


def test_fixture_count_and_split() -> None:
    """Sanity — exactly 20 fixtures, 10 bad / 10 good."""
    assert len(_FIXTURES) == 20, f"expected 20 fixtures, got {len(_FIXTURES)}"
    bad = [f for f in _FIXTURES if f["category"] == "bad"]
    good = [f for f in _FIXTURES if f["category"] == "good"]
    assert len(bad) == 10, f"expected 10 known-bad, got {len(bad)}"
    assert len(good) == 10, f"expected 10 known-good, got {len(good)}"


@pytest.mark.parametrize("fixture", _FIXTURES, ids=[f["id"] for f in _FIXTURES])
def test_precheck_smoke_status(fixture: dict) -> None:
    """Each fixture resolves to its expected deterministic status within budget."""
    path = _HERE / fixture["file"]
    assert path.exists(), f"fixture file missing: {path}"
    image_bytes = path.read_bytes()

    results, status, elapsed = _run_deterministic_checks(image_bytes)

    assert status == fixture["expected_status"], (
        f"{fixture['id']}: got status={status!r} "
        f"expected={fixture['expected_status']!r} (checks={results})"
    )
    assert elapsed <= _PILLOW_BUDGET_SECONDS, (
        f"{fixture['id']}: 4 Pillow checks took {elapsed:.3f}s "
        f"> {_PILLOW_BUDGET_SECONDS}s budget"
    )


def test_aggregate_verdict_and_write_results() -> None:
    """Run the full set, assert 20/20, and emit eval_results.json (Gate 2 evidence)."""
    bad_pass = 0
    good_pass = 0
    worst_time = 0.0
    failures: list[str] = []

    for fixture in _FIXTURES:
        image_bytes = (_HERE / fixture["file"]).read_bytes()
        results, status, elapsed = _run_deterministic_checks(image_bytes)
        worst_time = max(worst_time, elapsed)

        if status == fixture["expected_status"]:
            if fixture["category"] == "bad":
                bad_pass += 1
            else:
                good_pass += 1
        else:
            failures.append(
                f"{fixture['id']}: got={status} expected={fixture['expected_status']} "
                f"checks={results}"
            )

    total_pass = bad_pass + good_pass
    verdict = "PASS" if total_pass == 20 and worst_time <= _PILLOW_BUDGET_SECONDS else "FAIL"

    eval_results = {
        "run_date": "2026-06-11",
        "gate": "D2 Gate 2 — 4 deterministic Pillow checks (smoke)",
        "total_cases": len(_FIXTURES),
        "bad_pass": bad_pass,
        "good_pass": good_pass,
        "passed": total_pass,
        "bad_expected": 10,
        "good_expected": 10,
        "worst_case_pillow_seconds": round(worst_time, 4),
        "pillow_budget_seconds": _PILLOW_BUDGET_SECONDS,
        "gemini_calls": 0,
        "gemini_cost_inr": 0.0,
        "verdict": verdict,
    }
    (_HERE / "eval_results.json").write_text(json.dumps(eval_results, indent=2) + "\n")

    assert not failures, "status mismatches:\n  " + "\n  ".join(failures)
    assert bad_pass == 10, f"known-bad: {bad_pass}/10 -> failed_precheck"
    assert good_pass == 10, f"known-good: {good_pass}/10 -> ready"
    assert worst_time <= _PILLOW_BUDGET_SECONDS, (
        f"worst-case Pillow time {worst_time:.3f}s > {_PILLOW_BUDGET_SECONDS}s"
    )
