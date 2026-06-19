"""build_pricing_lookup.py — idempotent transform script for the MeeSell pricing lookup.

Reads:  logs/scraper/transfer_price_census_summary.json  (produced by meesell-scraper-maintainer)
Writes: backend/app/data/meesho_pricing_lookup.json       (shipped production data, committed)

HARD INVARIANTS (all three must hold; script exits non-zero on any violation):
  - error_rows == 0
  - len(lookup) == 3772
  - every row: commission_percentage == 0.0 AND formula_ok is True

This script is the SINGLE producer for both W1 (run once) and W6 (monthly refresh).
W6 will call this same script from the monthly scraper orchestrator.
Keep this file dependency-free (stdlib only).

Usage:
  python backend/scripts/build_pricing_lookup.py

Produces a stable, diff-friendly output (sort_keys=True, indent=2) so W6 monthly
refreshes emit minimal diffs when only shipping values change.
"""

import json
import subprocess
import sys
from pathlib import Path


def _find_repo_root() -> Path:
    """Locate the git working tree root.

    Works from both the main checkout and any worktree, because
    `git rev-parse --show-toplevel` always returns the worktree's own top-level
    directory — which shares logs/ in the COMMON git dir / worktree common location.

    For MeeSell worktrees under /tmp/mesell-wt/*  the logs/ directory lives only
    in the primary checkout at /Users/.../Project/mesell. We resolve the common
    directory path via `git rev-parse --git-common-dir` which points to the .git/
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
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "meesho_pricing_lookup.json"

EXPECTED_COUNT = 3772


def main() -> None:
    # 1. Read source
    if not CENSUS_PATH.exists():
        print(f"ERROR: census file not found at {CENSUS_PATH}", file=sys.stderr)
        sys.exit(1)

    with CENSUS_PATH.open(encoding="utf-8") as fh:
        census = json.load(fh)

    # 2. Hard invariants on the census itself
    error_rows: int = census.get("error_rows", -1)
    if error_rows != 0:
        print(
            f"ERROR: census has {error_rows} error_rows (expected 0). Refusing to emit a partial file.",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_lookup: dict = census.get("lookup", {})
    if len(raw_lookup) != EXPECTED_COUNT:
        print(
            f"ERROR: census lookup has {len(raw_lookup)} entries (expected {EXPECTED_COUNT}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # 3. Per-row validation + transform
    lookup: dict[str, dict] = {}
    bad_commission: list[str] = []
    bad_formula: list[str] = []

    for sscat_id, v in raw_lookup.items():
        commission = v["commission_percentage"]
        formula_ok = v["formula_ok"]

        if commission != 0.0:
            bad_commission.append(sscat_id)
        if formula_ok is not True:
            bad_formula.append(sscat_id)

        lookup[str(sscat_id)] = {
            "commission_percentage": 0,
            "shipping_charges": int(v["shipping_charges"]),
        }

    if bad_commission:
        print(
            f"ERROR: {len(bad_commission)} rows have non-zero commission_percentage: "
            f"{bad_commission[:5]}{'...' if len(bad_commission) > 5 else ''}",
            file=sys.stderr,
        )
        sys.exit(1)

    if bad_formula:
        print(
            f"ERROR: {len(bad_formula)} rows have formula_ok != True: "
            f"{bad_formula[:5]}{'...' if len(bad_formula) > 5 else ''}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 4. Build _meta from census top-level fields
    meta: dict = {
        "census_price": census["census_price"],
        "generated_at": census["generated_at"],
        "model": "confirmed-2026-06-19",
        "refresh": "monthly-via-scraper (W6 — folded into the existing monthly category scrape)",
        "source": "getTransferPrice census (logs/scraper/transfer_price_census_summary.json)",
        "total": len(lookup),
        "version": "1",
    }

    # 5. Final count check (after loop; guards against unexpected dict-key collision)
    if meta["total"] != EXPECTED_COUNT:
        print(
            f"ERROR: emitted lookup has {meta['total']} entries (expected {EXPECTED_COUNT}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # 6. Write output
    output: dict = {"_meta": meta, "lookup": lookup}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")  # POSIX newline at EOF

    print(
        f"OK: wrote {meta['total']} entries → {OUTPUT_PATH}\n"
        f"    generated_at={meta['generated_at']}\n"
        f"    census_price={meta['census_price']}\n"
        f"    commission=0 on all rows\n"
        f"    formula_ok=True on all rows\n"
        f"    error_rows=0"
    )


if __name__ == "__main__":
    main()
