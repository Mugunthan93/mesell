"""§19.C Contract 8 — ``scope_to_user`` enforcement on owned-table repositories.

Per BACKEND_ARCHITECTURE.md §19.C + §15.B (LOCKED 2026-06-06):

    Every public method on a repository.py that owns a tenant-scoped table
    MUST carry ``user_id`` in its signature. If a method's signature does NOT
    contain a ``user_id`` parameter, the test FAILS.

The §15.B 7-row owned-table matrix names 5 modules that own scope-able tables:

* customer  → seller_profile
* catalog   → catalogs / products / product_drafts
* image     → product_images
* pricing   → pricing_calcs
* export    → exports

The remaining 3 domain modules are allowlisted per §16.F + §15.B:

* category   → global tables per §16.F.2 (categories / templates /
               field_enum_values / field_aliases — no per-user scoping).
* dashboard  → no repository per §16.F.1 (composition layer only).
* iam        → users IS the principal subject per §15.B "Special-cased
               tables (neither pattern)". Methods key on phone / user_id
               directly because the row's identity == the principal.

Runnable via::

    python -m tests.lint.check_scope_to_user                    # exit 0 / 1
    python tests/lint/check_scope_to_user.py --root backend/    # explicit root

Importable via :func:`scan` + :func:`main` for the pytest wrapper at
``tests/lint/test_scope_to_user_enforcement.py``.

Pre-existing documented deviations
----------------------------------
Each entry in :data:`KNOWN_DEVIATIONS` documents a public repository method
that lacks ``user_id`` AND has its tenancy gate enforced upstream at the
service layer per a documented call site. Adding a new entry requires
both an inline citation and a STATUS_BACKEND.md / §15.B amendment.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# ── §15.B 7-row owned-table matrix — modules whose repository.py is scanned.
SCANNED_MODULES: tuple[str, ...] = (
    "customer",
    "catalog",
    "image",
    "pricing",
    "export",
)

# ── §16.F documented exceptions + §15.B "Special-cased" iam carve-out.
ALLOWLISTED_MODULES: frozenset[str] = frozenset({"category", "dashboard", "iam"})

# ── Pre-existing documented deviations — methods that lack ``user_id`` but
#    enforce tenancy at the upstream service-layer call site.
#
#    Each entry is fully-qualified ``app.modules.<m>.repository.<func>``.
#    Adding a new entry without a §15.B amendment is a §5.0 violation.
KNOWN_DEVIATIONS: frozenset[str] = frozenset({
    # ``pricing_calcs`` row insert. Per ``app/modules/pricing/repository.py``
    # ``insert_calc`` docstring (lines 8-11): "Tenancy gate is enforced
    # upstream — the ``product_id`` MUST belong to the calling user
    # (verified by ``catalog.assert_product_ownership`` before the insert)."
    # The cross-module gate at §12.C / §10.C is the §15.B Layer 2 enforcement
    # point; repository signature carries ``product_id`` because the
    # ``pricing_calcs`` table FKs on ``product_id`` (not ``user_id``) per the
    # §12.D schema. Cross-table tenancy holds because ``products.user_id``
    # was validated before this call.
    "app.modules.pricing.repository.insert_calc",
})


@dataclass(frozen=True)
class Violation:
    """One repository method that violates Contract 8."""

    module: str
    qualname: str
    file: str
    line: int
    reason: str

    def render(self) -> str:
        return (
            f"  • {self.file}:{self.line}  "
            f"{self.qualname}  ({self.reason})"
        )


def _repo_root(start: Path | None = None) -> Path:
    """Locate the ``backend/`` directory.

    Resolution order: explicit ``start`` argument → script-relative parents →
    cwd. Handles both ``cd backend && python -m tests.lint.check_scope_to_user``
    and direct script invocation from arbitrary CWDs.
    """
    if start is not None:
        return start.resolve()
    here = Path(__file__).resolve()
    # backend/tests/lint/check_scope_to_user.py → backend/
    for parent in here.parents:
        if (parent / "app" / "modules").is_dir():
            return parent
    raise RuntimeError(
        "Could not locate backend/ root from script path or cwd. "
        "Pass --root <backend-dir> explicitly."
    )


def _module_repository_path(repo_root: Path, module: str) -> Path:
    return repo_root / "app" / "modules" / module / "repository.py"


def _public_methods(tree: ast.Module) -> Iterable[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield every public top-level function in a repository.py module.

    Public = name does NOT start with ``_``. Nested defs are ignored — repository
    helpers are top-level by §3.C convention.
    """
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                yield node


def _has_user_id_param(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True iff ``user_id`` appears anywhere in the function signature.

    Checks positional, keyword-only, and positional-only argument lists. Does
    NOT introspect dataclass parameters — a parameter typed as a dataclass
    that itself carries ``user_id`` is NOT credited (the spec demands an
    explicit ``user_id`` parameter on the function signature).
    """
    arg_lists = (
        func.args.args,
        func.args.kwonlyargs,
        getattr(func.args, "posonlyargs", []) or [],
    )
    for arg_list in arg_lists:
        for arg in arg_list:
            if arg.arg == "user_id":
                return True
    return False


def scan(repo_root: Path | None = None) -> list[Violation]:
    """Walk every scanned repository.py, return the list of violations.

    Empty list = PASS. Non-empty list = FAIL with diagnostic detail.
    """
    root = _repo_root(repo_root)
    violations: list[Violation] = []

    for module in SCANNED_MODULES:
        path = _module_repository_path(root, module)
        if not path.is_file():
            violations.append(Violation(
                module=module,
                qualname=f"app.modules.{module}.repository",
                file=str(path),
                line=0,
                reason="repository.py MISSING (expected per §3.C canonical 7-file subtree)",
            ))
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover — defensive
            violations.append(Violation(
                module=module,
                qualname=f"app.modules.{module}.repository",
                file=str(path),
                line=exc.lineno or 0,
                reason=f"SyntaxError: {exc.msg}",
            ))
            continue

        for func in _public_methods(tree):
            qualname = f"app.modules.{module}.repository.{func.name}"
            if qualname in KNOWN_DEVIATIONS:
                continue
            if _has_user_id_param(func):
                continue
            violations.append(Violation(
                module=module,
                qualname=qualname,
                file=str(path),
                line=func.lineno,
                reason="missing `user_id` parameter — §15.B owned-table rule",
            ))

    return violations


def main(argv: list[str] | None = None) -> int:
    """CLI entry — return 0 on PASS, 1 on FAIL.

    Output is intentionally human-readable: one line per violation, prefixed
    with a bullet so it copy-pastes cleanly into PR review threads.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Path to backend/ root (default: auto-detect).",
    )
    args = parser.parse_args(argv)

    violations = scan(args.root)
    if not violations:
        print(
            "§19.C Contract 8 PASS — every public repository method on "
            f"{len(SCANNED_MODULES)} owned-table modules carries `user_id`."
        )
        return 0

    print(
        f"§19.C Contract 8 FAIL — {len(violations)} repository method(s) "
        "violate the §15.B `scope_to_user` rule:",
        file=sys.stderr,
    )
    for v in violations:
        print(v.render(), file=sys.stderr)
    print(
        "\nRemediation: add `user_id: UUID` to the signature OR add a "
        "documented entry to `KNOWN_DEVIATIONS` with an inline citation of "
        "the upstream tenancy gate.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
