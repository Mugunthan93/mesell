# project — Picker V1 pure-Python helpers LOCKED

**Date:** 2026-06-07
**Sub-session:** §9 `category` module construction (AI track contribution)
**Status:** LOCKED — services-builder and api-routes-builder may consume verbatim.

## Files written

| Path | Role |
|---|---|
| `backend/app/modules/category/__init__.py` | Package docstring; AI-seam disclaimer per §9.A |
| `backend/app/modules/category/picker.py` | Three public pure functions (no I/O) |
| `backend/tests/modules/category/__init__.py` | Test package stub |
| `backend/tests/modules/category/test_picker_helpers.py` | 4 unit tests, all PASS |
| `backend/tests/eval/__init__.py` | V1.5 golden-eval stub |
| `backend/tests/eval/smart_picker/__init__.py` | V1.5 golden-eval stub |
| `backend/tests/eval/smart_picker/fixtures.json` | `{"fixtures": [], "version": "v1", "owner": "meesell-prompt-engineer", "status": "V1.5_TODO_50_descriptions"}` |

## LOCKED contract — `picker.py` public surface

```python
def compress_tree(
    category_rows: Iterable[Any],   # accepts §9.F CategoryRow OR dict OR any attr-bearing obj
    description: str | None = None,
) -> dict[str, Any]:
    """
    Returns JSON-serialisable dict:
      {"super_categories": [
         {"super_id": str, "super_name": str,
          "leaves": [{"category_id": str, "leaf_name": str, "path": str}, ... up to 50]},
         ...sorted by super_id ASC
      ]}
    Bit-deterministic; per-leaf trigram overlap with description biases the leaf sample.
    """

def calibrate_confidence(
    raw_ai_confidence: float,
    layer2_retries: int = 0,
) -> float:
    """Penalty = 0.1 per retry; clamped to [0.0, 1.0]; safe for §9.E Field(ge=0, le=1)."""

def select_top_k(
    scored_suggestions: list[dict[str, Any]],
    k: int = 5,
) -> list[dict[str, Any]]:
    """Sort by confidence DESC, tie-break on category_id ASC; input not mutated; k<=0 → []."""
```

## Tunables (module-private)
- `_MAX_LEAVES_PER_SUPER = 50` — sized against §6A.D smart_picker 32K token cap.
- `_TRIGRAM_N = 3` — matches pg_trgm default so AI ranking ≈ /browse ranking.
- `_RETRY_PENALTY = 0.1` — 0/1/2 retries → penalty 0/0.1/0.2 per §6A.E.

## Test results
- `ruff check backend/app/modules/category/picker.py backend/tests/modules/category/test_picker_helpers.py` → All checks passed.
- `pytest backend/tests/modules/category/test_picker_helpers.py -v` → 4 passed in 0.02s (Python 3.11.14, pytest 8.3.0, project venv).

## Hand-off notes
- `services-builder` (`category.service.suggest_categories` per §9.C):
  - call `compress_tree(rows, q)` → pass as `prompt_vars["compressed_tree"]` to `ai_ops.client.call_gemini(ctx, "smart_picker.v1", {"description": q, "compressed_tree": <out>})`.
  - For each raw AI suggestion: `confidence = calibrate_confidence(raw["confidence"], ai_response.layer2_retries)`.
  - Then `select_top_k(scored, k=5)` before mapping to `CategorySuggestion` (§9.E).
- `prompt-engineer`: prompt template at `backend/app/ai_ops/prompts/smart_picker_v1.py` already references `{{compressed_tree}}` — output shape MATCHES. No changes required for V1.
- `api-routes-builder`: no direct dependency on this module; consumes the service surface only.

## Hard rules upheld
- No I/O (pure functions).
- No `adapters/gemini` import.
- No new third-party deps (stdlib only).
- Deterministic output (cache-key safe).
- Did NOT modify `smart_picker_v1.py` (prompt-engineer owns content).

## V1.5 follow-ups
- Populate `backend/tests/eval/smart_picker/fixtures.json` with 50 hand-labeled descriptions for the golden eval (`MVP_ARCH §8.5` ≥ 80% top-5 recall).
- Consider an embedding pre-filter to drop super-categories with zero trigram overlap from the compressed tree (token savings).
- Revisit `_RETRY_PENALTY` if golden eval shows the floor over-aggressively pushes good suggestions below frontend's display threshold.
