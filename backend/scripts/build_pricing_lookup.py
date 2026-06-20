"""build_pricing_lookup.py — idempotent transform script for the MeeSell pricing lookup.

Reads:  logs/scraper/transfer_price_census_summary.json  (produced by meesell-scraper-maintainer)
Writes: backend/app/data/meesho_pricing_lookup.json       (shipped production data, committed)

HARD INVARIANTS (all must hold; the script exits non-zero on any violation):
  - error_rows == 0
  - len(lookup) == 3772
  - every row: commission_percentage == 0.0 AND formula_ok is True
  - final emitted lookup count == 3772

These invariants are the same whether the script runs in no-arg mode (W1) or
--candidate-out mode (W6 monthly refresh).  The gate is a hard barrier in both cases.

W6 CANDIDATE MODE (--candidate-out <path>):
  Instead of overwriting the committed file, write the validated candidate to the
  given path.  The orchestrator (meesho_monthly_refresh.py) then runs the drift
  gate (diff_pricing_lookup.py) before deciding whether to promote.

  When --candidate-out is supplied the function ``build(candidate_out=path)`` also
  returns a verdict dict to programmatic callers:
      {
          "ok":     True | False,
          "reason": str,           # human-readable; "" when ok is True
          "output": Path | None,   # path the candidate was written to (or None on fail)
      }

This script is the SINGLE producer for both W1 (run once) and W6 (monthly refresh).
Keep this file dependency-free (stdlib only).

Usage:
  # W1 / standalone — writes directly to the committed file:
  python backend/scripts/build_pricing_lookup.py

  # W6 / monthly refresh — writes candidate to side path, does not touch live file:
  python backend/scripts/build_pricing_lookup.py --candidate-out logs/scraper/meesho_pricing_lookup.candidate.json

Produces a stable, diff-friendly output (sort_keys=True, indent=2) so monthly
refreshes emit minimal diffs when only shipping values change.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    """Locate the git working tree root.

    Works from both the main checkout and any worktree, because
    ``git rev-parse --show-toplevel`` always returns the worktree's own top-level
    directory — which shares logs/ in the COMMON git dir / worktree common location.

    For MeeSell worktrees under /tmp/mesell-wt/*  the logs/ directory lives only
    in the primary checkout at /Users/.../Project/mesell.  We resolve the common
    directory path via ``git rev-parse --git-common-dir`` which points to the .git/
    of the primary checkout, then climb one level.
    """
    try:
        common_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=Path(__file__).parent,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        # --git-common-dir returns an absolute path (or relative to cwd for linked worktrees).
        common_path = Path(common_dir)
        if not common_path.is_absolute():
            common_path = (Path(__file__).parent / common_path).resolve()
        # The common .git dir is <repo_root>/.git  → parent is the repo root.
        repo_root = common_path.parent
        return repo_root
    except Exception:
        # Fallback: 3 levels up from this script (works when run from the primary checkout).
        return Path(__file__).resolve().parent.parent.parent


# ---- Paths ---------------------------------------------------------------
REPO_ROOT = _find_repo_root()
CENSUS_PATH = REPO_ROOT / "logs" / "scraper" / "transfer_price_census_summary.json"
_DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "data" / "meesho_pricing_lookup.json"
)
# Backward-compat alias used by W1 callers who reference this symbol directly.
OUTPUT_PATH = _DEFAULT_OUTPUT_PATH

EXPECTED_COUNT = 3772


def build(
    census_path: Path | None = None,
    candidate_out: Path | None = None,
) -> dict[str, Any]:
    """Run the transform pipeline and return a verdict dict.

    This is the programmatic entry point for the W6 orchestrator.
    ``main()`` calls this and translates the verdict into an exit code.

    Args:
        census_path:   Path to the census summary JSON.  Defaults to
                       ``CENSUS_PATH`` (``logs/scraper/transfer_price_census_summary.json``).
        candidate_out: When provided, write the validated candidate to this path
                       INSTEAD OF the committed ``meesho_pricing_lookup.json``.
                       The live file is never touched in candidate mode.
                       When None, the live committed file is overwritten (W1 / no-arg behaviour).

    Returns:
        A verdict dict::

            {
                "ok":     True | False,
                "reason": str,       # "" when ok is True; human-readable error when False
                "output": Path | None,  # file that was written; None when ok is False
            }

    IMPORTANT:  This function NEVER calls ``sys.exit()``.  Only ``main()`` / ``_cli()``
    call sys.exit().  This keeps the programmatic interface clean for the orchestrator.
    """
    src_path = census_path if census_path is not None else CENSUS_PATH
    out_path = candidate_out if candidate_out is not None else _DEFAULT_OUTPUT_PATH

    # 1. Read source
    if not src_path.exists():
        return {
            "ok": False,
            "reason": f"census file not found at {src_path}",
            "output": None,
        }

    with src_path.open(encoding="utf-8") as fh:
        census = json.load(fh)

    # 2. Hard invariant: error_rows == 0
    error_rows: int = census.get("error_rows", -1)
    if error_rows != 0:
        return {
            "ok": False,
            "reason": (
                f"census has {error_rows} error_rows (expected 0). "
                "Refusing to emit a partial file."
            ),
            "output": None,
        }

    # 3. Hard invariant: census lookup count == EXPECTED_COUNT
    raw_lookup: dict = census.get("lookup", {})
    if len(raw_lookup) != EXPECTED_COUNT:
        return {
            "ok": False,
            "reason": (
                f"census lookup has {len(raw_lookup)} entries "
                f"(expected {EXPECTED_COUNT})."
            ),
            "output": None,
        }

    # 4. Per-row validation + transform
    lookup: dict[str, dict] = {}
    bad_commission: list[str] = []
    bad_formula: list[str] = []

    for sscat_id, v in raw_lookup.items():
        commission = v["commission_percentage"]
        formula_ok = v["formula_ok"]

        if commission != 0.0:
            bad_commission.append(str(sscat_id))
        if formula_ok is not True:
            bad_formula.append(str(sscat_id))

        lookup[str(sscat_id)] = {
            "commission_percentage": 0,
            "shipping_charges": int(v["shipping_charges"]),
        }

    if bad_commission:
        return {
            "ok": False,
            "reason": (
                f"{len(bad_commission)} rows have non-zero commission_percentage: "
                f"{bad_commission[:5]}{'...' if len(bad_commission) > 5 else ''}"
            ),
            "output": None,
        }

    if bad_formula:
        return {
            "ok": False,
            "reason": (
                f"{len(bad_formula)} rows have formula_ok != True: "
                f"{bad_formula[:5]}{'...' if len(bad_formula) > 5 else ''}"
            ),
            "output": None,
        }

    # 5. Build _meta from census top-level fields
    meta: dict = {
        "census_price": census["census_price"],
        "generated_at": census["generated_at"],
        "model": "confirmed-2026-06-19",
        "refresh": "monthly-via-scraper (W6 — folded into the existing monthly category scrape)",
        "source": "getTransferPrice census (logs/scraper/transfer_price_census_summary.json)",
        "total": len(lookup),
        "version": "1",
    }

    # 6. Final count guard (post-loop; catches unexpected key collisions)
    if meta["total"] != EXPECTED_COUNT:
        return {
            "ok": False,
            "reason": (
                f"emitted lookup has {meta['total']} entries "
                f"(expected {EXPECTED_COUNT})."
            ),
            "output": None,
        }

    # 7. Write output (to candidate path or live path)
    output_doc: dict = {"_meta": meta, "lookup": lookup}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(output_doc, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")  # POSIX newline at EOF

    return {"ok": True, "reason": "", "output": out_path}


def main() -> None:
    """CLI entry point.  Parses --candidate-out then delegates to build()."""
    candidate_out: Path | None = _parse_candidate_out()
    verdict = build(candidate_out=candidate_out)

    if not verdict["ok"]:
        print(f"ERROR: {verdict['reason']}", file=sys.stderr)
        sys.exit(1)

    out = verdict["output"]
    mode = "candidate" if candidate_out is not None else "live"
    print(
        f"OK [{mode}]: wrote {EXPECTED_COUNT} entries → {out}\n"
        f"    commission=0 on all rows\n"
        f"    formula_ok=True on all rows\n"
        f"    error_rows=0"
    )


def _parse_candidate_out() -> Path | None:
    """Parse --candidate-out <path> from sys.argv without importing argparse.

    Returns the Path if supplied, else None.
    Keeps the module import-free at the top level (stdlib-only, no argparse at import time).
    """
    argv = sys.argv[1:]
    if "--candidate-out" in argv:
        idx = argv.index("--candidate-out")
        if idx + 1 >= len(argv):
            print("ERROR: --candidate-out requires a path argument.", file=sys.stderr)
            sys.exit(1)
        return Path(argv[idx + 1])
    return None


if __name__ == "__main__":
    main()
