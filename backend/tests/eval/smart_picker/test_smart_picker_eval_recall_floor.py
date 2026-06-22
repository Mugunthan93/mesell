"""CAT-BE-EVAL  Smart Category Picker — pytest gate for golden recall floor.

This is the pytest wrapper around the logic in ``run_eval.py``.  It:

1.  Loads ``picker.py`` in isolation (bypassing the FastAPI env gate, exactly
    as the standalone runner does).
2.  Loads the 3,772-leaf tree from ``app/data/meesho_category_tree.json``.
3.  Scores all 50 golden fixtures in ``fixtures.json`` using the picker's own
    trigram-overlap ranker — NO live Gemini call, NO DB, NO Valkey.
4.  Asserts that top-5 recall >= 80% (>=40/50 descriptions surface the expected
    leaf in the top-5 by overlap score).

Contract per §22.C / V1_FEATURE_SPEC Feature 2:
    ``top-5 recall >= 80% over 50 hand-labelled descriptions``

This test SKIPS (not fails) when the tree file is absent, so CI (schema-only)
degrades gracefully.  It only FAILS when the tree IS present AND recall
drops below the floor — which is the actionable signal.

No monkeypatching needed — pure function evaluation.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_BACKEND_ROOT = _HERE.parents[2]  # tests/eval/smart_picker -> backend/
_TREE_PATH = _BACKEND_ROOT / "app" / "data" / "meesho_category_tree.json"
_PICKER_PATH = _BACKEND_ROOT / "app" / "modules" / "category" / "picker.py"
_FIXTURES_PATH = _HERE / "fixtures.json"

_THRESHOLD_PCT = 80.0  # must match run_eval.py
_TOP_K = 5


pytestmark = pytest.mark.ai_eval


# ─────────────────────────────────────────────────────────────────────────────
# Helper: load picker.py in isolation (no env-gate side-effects)
# ─────────────────────────────────────────────────────────────────────────────

def _load_picker():
    """Load picker.py bypassing the app package env gate (importlib isolation)."""
    spec = importlib.util.spec_from_file_location("picker_iso", _PICKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_leaves() -> list[dict]:
    """Read meesho_category_tree.json and return flat leaf list."""
    tree = json.loads(_TREE_PATH.read_text())
    return [
        {"leaf_name": c["leaf_name"], "path": " > ".join(c["path"])}
        for c in tree["categories"]
    ]


def _top5_paths(picker, leaves: list[dict], description: str) -> list[str]:
    """Rank leaves by picker's trigram-overlap signal; return top-5 paths."""
    q_trigrams = picker._trigrams(description)
    scored = []
    for leaf in leaves:
        leaf_text = f"{leaf['leaf_name']} {leaf['path']}"
        overlap = picker._overlap(picker._trigrams(leaf_text), q_trigrams)
        scored.append((overlap, leaf["leaf_name"], leaf["path"]))
    # Deterministic sort: overlap DESC, leaf_name ASC, path ASC.
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))
    return [path for _, _, path in scored[:_TOP_K]]


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-EVAL: top-5 recall floor
# ─────────────────────────────────────────────────────────────────────────────

def test_smart_picker_eval_recall_floor():
    """CAT-BE-EVAL: smart_picker top-5 recall must be >= 80% (40/50 fixtures).

    Skips gracefully when the tree file is absent (CI schema-only).
    Fails with diagnostic output when recall drops below the floor.
    """
    if not _TREE_PATH.exists():
        pytest.skip(
            f"meesho_category_tree.json not found at {_TREE_PATH}; "
            "skip eval gate (CI schema-only, seed absent)"
        )

    if not _FIXTURES_PATH.exists():
        pytest.skip(f"fixtures.json not found at {_FIXTURES_PATH}; skip eval gate")

    picker = _load_picker()
    leaves = _load_leaves()
    fixtures = json.loads(_FIXTURES_PATH.read_text())

    assert isinstance(fixtures, list), "fixtures.json must be a JSON list"
    assert len(fixtures) > 0, "fixtures.json must contain at least one fixture"

    passed = 0
    failures: list[str] = []

    for fix in fixtures:
        accept = set(fix.get("min_acceptable_paths") or [fix["expected_category_path"]])
        top5 = _top5_paths(picker, leaves, fix["description"])
        hit = any(p in accept for p in top5)
        if hit:
            passed += 1
        else:
            failures.append(
                f"  [{fix['id']}] description={fix['description'][:60]!r}\n"
                f"    expected one of: {sorted(accept)}\n"
                f"    got top5       : {top5}"
            )

    total = len(fixtures)
    accuracy_pct = round(100.0 * passed / total, 1) if total else 0.0
    verdict = "PASS" if accuracy_pct >= _THRESHOLD_PCT else "FAIL"

    # Diagnostic output for failures.
    if failures:
        diagnostic = "\n".join(failures)
        print(f"\n[CAT-BE-EVAL] {len(failures)} fixture(s) missed:\n{diagnostic}")

    print(
        f"\n[CAT-BE-EVAL] smart_picker top-5 recall: "
        f"{passed}/{total} = {accuracy_pct}%  (floor={int(_THRESHOLD_PCT)}%)"
        f"  verdict={verdict}"
    )

    assert accuracy_pct >= _THRESHOLD_PCT, (
        f"smart_picker top-5 recall {accuracy_pct}% is below the "
        f"{int(_THRESHOLD_PCT)}% gate ({passed}/{total} passed).\n"
        f"Failures:\n" + "\n".join(failures)
    )
