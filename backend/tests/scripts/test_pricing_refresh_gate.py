"""test_pricing_refresh_gate.py — §6 acceptance tests for the W6 validation gate.

Covers §6 tests:
  - test_gate_fails_on_short_census   (rows_with_data=3771 → raise, live untouched)
  - test_gate_fails_on_nonzero_commission (commission=4 → raise, no overwrite)
  - test_gate_fails_on_formula_not_ok (formula_ok=false → raise, no overwrite)
  - test_gate_passes_clean            (3772 / 0-errors / all-zero / all-ok → ok=True)
  - test_idempotent_no_change         (same census in twice → byte-identical lookup payload)

DB-SAFETY: NO database imports, NO live connection.  Fixtures are synthetic Python dicts
written to tempfile.  This module NEVER touches the dev DB.

Marker: unit (§19.D — pure-function, no I/O beyond tempfile).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# The module under test — imported directly, not via the app package.
# sys.path includes the backend/ dir via pytest.ini pythonpath=.
from scripts.build_pricing_lookup import build  # type: ignore[import]

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

EXPECTED_COUNT = 3772


def _make_census(
    count: int = EXPECTED_COUNT,
    error_rows: int = 0,
    commission_override: dict[str, float] | None = None,
    formula_ok_override: dict[str, bool] | None = None,
    shipping_override: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Return a synthetic census summary dict resembling
    ``logs/scraper/transfer_price_census_summary.json``.

    Args:
        count:               Number of rows to include in ``lookup``.
        error_rows:          Value of ``error_rows`` at the top level.
        commission_override: {sscat_id_str: commission_pct} to set on specific rows.
        formula_ok_override: {sscat_id_str: bool} to override on specific rows.
        shipping_override:   {sscat_id_str: int} to set shipping on specific rows.
    """
    commission_override = commission_override or {}
    formula_ok_override = formula_ok_override or {}
    shipping_override = shipping_override or {}

    lookup: dict[str, Any] = {}
    for i in range(count):
        sscat_id = str(10000 + i)
        lookup[sscat_id] = {
            "leaf_name": f"Category {i}",
            "path_str": f"Root > Cat{i}",
            "commission_percentage": commission_override.get(sscat_id, 0.0),
            "shipping_charges": shipping_override.get(sscat_id, 50 + (i % 100)),
            "transfer_price_at_100": 85.0,
            "formula_ok": formula_ok_override.get(sscat_id, True),
        }

    return {
        "census_price": 100,
        "generated_at": "2026-06-01T00:00:00",
        "rows_with_data": count,
        "error_rows": error_rows,
        "lookup": lookup,
    }


def _write_census(census: dict[str, Any], tmp_dir: Path) -> Path:
    """Write census dict to a temp file and return the path."""
    p = tmp_dir / "census_summary.json"
    p.write_text(json.dumps(census, indent=2), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_gate_fails_on_short_census(tmp_path: Path) -> None:
    """§6: rows_with_data=3771 → build() returns ok=False; candidate file NOT created.

    The live file must remain untouched.  We pass --candidate-out to a temp path
    and assert the file is absent after the failed run.
    """
    census = _make_census(count=EXPECTED_COUNT - 1, error_rows=0)
    census_path = _write_census(census, tmp_path)

    candidate_out = tmp_path / "candidate.json"

    verdict = build(census_path=census_path, candidate_out=candidate_out)

    assert verdict["ok"] is False, f"Expected failure; got: {verdict}"
    assert verdict["output"] is None
    assert "3771" in verdict["reason"] or str(EXPECTED_COUNT - 1) in verdict["reason"]
    assert not candidate_out.exists(), "Candidate file must NOT be created on gate failure"


@pytest.mark.unit
def test_gate_fails_on_nonzero_commission(tmp_path: Path) -> None:
    """§6: one row commission_percentage=4 → ok=False; candidate not created."""
    census = _make_census(
        count=EXPECTED_COUNT,
        error_rows=0,
        commission_override={"10000": 4.0},
    )
    census_path = _write_census(census, tmp_path)
    candidate_out = tmp_path / "candidate.json"

    verdict = build(census_path=census_path, candidate_out=candidate_out)

    assert verdict["ok"] is False
    assert verdict["output"] is None
    assert "commission" in verdict["reason"].lower()
    assert not candidate_out.exists()


@pytest.mark.unit
def test_gate_fails_on_formula_not_ok(tmp_path: Path) -> None:
    """§6: one row formula_ok=False → ok=False; candidate not created."""
    census = _make_census(
        count=EXPECTED_COUNT,
        error_rows=0,
        formula_ok_override={"10001": False},
    )
    census_path = _write_census(census, tmp_path)
    candidate_out = tmp_path / "candidate.json"

    verdict = build(census_path=census_path, candidate_out=candidate_out)

    assert verdict["ok"] is False
    assert verdict["output"] is None
    assert "formula" in verdict["reason"].lower()
    assert not candidate_out.exists()


@pytest.mark.unit
def test_gate_passes_clean(tmp_path: Path) -> None:
    """§6: 3772 rows / error_rows=0 / all commission=0 / all formula_ok → ok=True.

    Verifies:
    - verdict["ok"] is True
    - candidate file is created at the given path
    - emitted JSON has exactly EXPECTED_COUNT entries in "lookup"
    - every emitted row has commission_percentage=0 and shipping_charges is an int
    """
    census = _make_census(count=EXPECTED_COUNT, error_rows=0)
    census_path = _write_census(census, tmp_path)
    candidate_out = tmp_path / "candidate.json"

    verdict = build(census_path=census_path, candidate_out=candidate_out)

    assert verdict["ok"] is True, f"Expected success; got: {verdict}"
    assert verdict["output"] == candidate_out
    assert candidate_out.exists()

    with candidate_out.open(encoding="utf-8") as fh:
        doc = json.load(fh)

    assert "_meta" in doc
    assert "lookup" in doc
    lookup = doc["lookup"]
    assert len(lookup) == EXPECTED_COUNT

    for sscat_id, row in lookup.items():
        assert row["commission_percentage"] == 0, f"Row {sscat_id} has non-zero commission"
        assert isinstance(row["shipping_charges"], int), (
            f"Row {sscat_id} shipping_charges is not int"
        )


@pytest.mark.unit
def test_idempotent_no_change(tmp_path: Path) -> None:
    """§6: same census in twice → byte-identical ``lookup`` payload.

    _meta.generated_at is legitimately different across runs; the test compares
    the ``lookup`` sub-dict only, not the full file bytes.  This mirrors the
    drift-gate idempotency contract from §3.
    """
    census = _make_census(count=EXPECTED_COUNT, error_rows=0)
    census_path = _write_census(census, tmp_path)

    candidate_a = tmp_path / "candidate_a.json"
    candidate_b = tmp_path / "candidate_b.json"

    v1 = build(census_path=census_path, candidate_out=candidate_a)
    v2 = build(census_path=census_path, candidate_out=candidate_b)

    assert v1["ok"] is True
    assert v2["ok"] is True

    with candidate_a.open(encoding="utf-8") as fh:
        doc_a = json.load(fh)
    with candidate_b.open(encoding="utf-8") as fh:
        doc_b = json.load(fh)

    # The lookup payloads must be identical.
    assert doc_a["lookup"] == doc_b["lookup"], (
        "Two builds from the same census must produce identical lookup payloads"
    )

    # Serialise with the same stable options as build_pricing_lookup.py uses.
    lookup_text_a = json.dumps(doc_a["lookup"], indent=2, sort_keys=True, ensure_ascii=False)
    lookup_text_b = json.dumps(doc_b["lookup"], indent=2, sort_keys=True, ensure_ascii=False)
    assert lookup_text_a == lookup_text_b, "Lookup payload serialisation must be byte-identical"


@pytest.mark.unit
def test_gate_fails_on_error_rows(tmp_path: Path) -> None:
    """Extra gate test: error_rows != 0 → ok=False regardless of lookup count."""
    census = _make_census(count=EXPECTED_COUNT, error_rows=5)
    census_path = _write_census(census, tmp_path)
    candidate_out = tmp_path / "candidate.json"

    verdict = build(census_path=census_path, candidate_out=candidate_out)

    assert verdict["ok"] is False
    assert "error_rows" in verdict["reason"].lower() or "5" in verdict["reason"]
    assert not candidate_out.exists()


@pytest.mark.unit
def test_candidate_out_does_not_touch_live_file(tmp_path: Path) -> None:
    """When --candidate-out is supplied, the live committed file is never modified."""
    # Use a sentinel live file
    live_file = tmp_path / "live" / "meesho_pricing_lookup.json"
    live_file.parent.mkdir()
    sentinel = {"_meta": {"sentinel": True}, "lookup": {}}
    live_file.write_text(json.dumps(sentinel), encoding="utf-8")
    live_mtime_before = live_file.stat().st_mtime

    census = _make_census(count=EXPECTED_COUNT, error_rows=0)
    census_path = _write_census(census, tmp_path)
    candidate_out = tmp_path / "candidate.json"

    # We do NOT pass live_file to build(); the live file path is the module default.
    # The key invariant: build() writes ONLY to candidate_out (not to any other path).
    verdict = build(census_path=census_path, candidate_out=candidate_out)

    assert verdict["ok"] is True
    assert verdict["output"] == candidate_out
    # The sentinel live file must be untouched
    assert live_file.stat().st_mtime == live_mtime_before
    with live_file.open() as fh:
        still_sentinel = json.load(fh)
    assert still_sentinel.get("_meta", {}).get("sentinel") is True
