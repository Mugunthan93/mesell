#!/usr/bin/env python3
"""Smart Category Picker — golden eval runner (V1 Feature 2).

Token-free, deterministic eval of the picker's recall against the real
3,772-leaf Meesho category tree. We cannot call live Gemini at audit time
(token cost + no API key in CI), so this runner exercises the SAME signal
Gemini sees: the trigram-overlap ranking that
``app.modules.category.picker.compress_tree`` uses to choose which leaves
to surface in the compressed prompt.

The contract being validated (§22.C / V1_FEATURE_SPEC Feature 2):
    top-5 recall >= 80% over 50 hand-labelled descriptions
    (>= 40/50 descriptions surface the expected leaf path in the top-5).

Method per fixture:
  1. Score every leaf in the full tree by trigram overlap between the
     fixture description and the leaf's ``"<leaf_name> <path>"`` text,
     using picker._trigrams / picker._overlap (the picker's own functions
     — no re-implementation, so the eval tracks the production ranker).
  2. Take the top-5 leaves by (overlap DESC, leaf_name ASC, path ASC).
  3. PASS if any of the fixture's ``min_acceptable_paths`` is in that top-5.

picker.py is loaded IN ISOLATION via importlib (loading the package
``app.modules.category.picker`` triggers env-var validation that FATALs
outside a configured runtime). picker.py is pure stdlib, so this works.

Run:
    python3 backend/tests/eval/smart_picker/run_eval.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND_ROOT = _HERE.parents[2]  # tests/eval/smart_picker -> backend/
_TREE_PATH = _BACKEND_ROOT / "app" / "data" / "meesho_category_tree.json"
_PICKER_PATH = _BACKEND_ROOT / "app" / "modules" / "category" / "picker.py"
_FIXTURES_PATH = _HERE / "fixtures.json"
_RESULTS_PATH = _HERE / "eval_results.json"

_THRESHOLD_PCT = 80.0
_TOP_K = 5


def _load_picker():
    """Load picker.py in isolation, bypassing the app package env gate."""
    spec = importlib.util.spec_from_file_location("picker_iso", _PICKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_leaves() -> list[dict]:
    tree = json.loads(_TREE_PATH.read_text())
    return [
        {"leaf_name": c["leaf_name"], "path": " > ".join(c["path"])}
        for c in tree["categories"]
    ]


def _top5_paths(picker, leaves: list[dict], description: str) -> list[str]:
    """Rank all leaves by the picker's trigram-overlap signal, return top-5 paths."""
    q_trigrams = picker._trigrams(description)
    scored = []
    for leaf in leaves:
        leaf_text = f"{leaf['leaf_name']} {leaf['path']}"
        overlap = picker._overlap(picker._trigrams(leaf_text), q_trigrams)
        scored.append((overlap, leaf["leaf_name"], leaf["path"]))
    # overlap DESC, leaf_name ASC, path ASC — total + deterministic
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))
    return [path for _, _, path in scored[:_TOP_K]]


def main() -> int:
    picker = _load_picker()
    leaves = _load_leaves()
    fixtures = json.loads(_FIXTURES_PATH.read_text())
    if not isinstance(fixtures, list):
        raise ValueError("fixtures.json must be a JSON list")

    passed = 0
    for fix in fixtures:
        accept = set(fix.get("min_acceptable_paths") or [fix["expected_category_path"]])
        top5 = _top5_paths(picker, leaves, fix["description"])
        hit = any(p in accept for p in top5)
        status = "PASS" if hit else "FAIL"
        if hit:
            passed += 1
        else:
            print(f"  [{status}] {fix['id']}: {fix['description'][:55]!r}")
            print(f"          expected one of: {sorted(accept)}")
            print(f"          got top5       : {top5}")

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
    }
    _RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")

    print(
        f"\nsmart_picker: {passed}/{total} top-5 recall "
        f"accuracy={accuracy_pct}% threshold={int(_THRESHOLD_PCT)}% "
        f"verdict={verdict}"
    )
    print(f"wrote {_RESULTS_PATH}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
