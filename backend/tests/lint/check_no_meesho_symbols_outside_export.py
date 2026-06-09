"""§19.C Contract 9 — M10 forbidden-symbol scanner.

Per BACKEND_ARCHITECTURE.md §19.C + §14.J + §15.F + §0.H (LOCKED 2026-06-06):

    The three M10 symbols
        * ``meesho_column_header``
        * ``meesho_column_index``
        * ``enum_codes_map``
    MUST NOT appear as identifiers (name / attribute / keyword / parameter)
    anywhere under ``app/`` outside the explicitly-allowlisted subtrees.

Allowlisted subtrees (locked at §14.J + §16.F):

* ``app/modules/export/**``   — the M10 boundary lives here per §14.J
* ``app/adapters/gcs.py``     — write-path may carry the symbols as method
                                  argument names per §14.J prose.

Detection model (locked per L_export_M10_AST_scanner — STATUS_BACKEND line
38): walking name resolution + attribute access is the actual M10 check.
String-literal mentions inside docstrings are NOT flagged — distinguishing
docstring strings from runtime symbol usage is the spec posture.

Pre-existing docstring hits OUTSIDE the export subtree
------------------------------------------------------
:data:`KNOWN_DOCSTRING_HITS` documents the locations where the M10 symbols
appear inside a string literal (typically a JSON-shape example in a model
docstring). These are NOT flagged by the current scanner — the set is
forward-compat documentation for any future extension that also walks
``ast.Constant``. Adding a new entry without a §14.J amendment is a §5.0
violation.

Runnable via::

    python -m tests.lint.check_no_meesho_symbols_outside_export
    python tests/lint/check_no_meesho_symbols_outside_export.py --root backend/

Importable via :func:`scan` + :func:`main` for the pytest wrapper at
``tests/lint/test_no_meesho_symbols_outside_export.py``.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

# ── §14.J + §15.F locked forbidden-symbol set.
FORBIDDEN_SYMBOLS: frozenset[str] = frozenset({
    "meesho_column_header",
    "meesho_column_index",
    "enum_codes_map",
})

# ── Path-prefix allowlist — symbols permitted inside these subtrees.
#    Stored as POSIX-style relative paths anchored at backend/.
ALLOWED_PATH_PREFIXES: tuple[str, ...] = (
    "app/modules/export/",
    "app/adapters/gcs.py",
)

# ── Known docstring-only mentions per L_export_M10_AST_scanner (STATUS_BACKEND
#    2026-06-08 line 38). Each entry is (relative_path, line_no, symbol).
#
#    The current scanner does NOT flag string-literal hits (per
#    L_export_M10_AST_scanner: "walking name resolution + attribute access is
#    the actual M10 check"). This frozenset is forward-compat documentation
#    so a future extension that adds ``ast.Constant`` walking knows which
#    pre-existing hits to allowlist.
KNOWN_DOCSTRING_HITS: frozenset[tuple[str, int, str]] = frozenset({
    # JSON-shape example in the Template ORM model docstring.
    ("app/shared/models/template.py", 37, "meesho_column_header"),
    ("app/shared/models/template.py", 38, "meesho_column_index"),
    ("app/shared/models/template.py", 40, "enum_codes_map"),
    # Module docstring inside the (already allowlisted) export subtree.
    # Listed for completeness per L_export_M10_AST_scanner.
    ("app/modules/export/__init__.py", 19, "meesho_column_header"),
    ("app/modules/export/__init__.py", 20, "enum_codes_map"),
    ("app/modules/export/schemas.py", 0, "meesho_column_header"),
})


@dataclass(frozen=True)
class Violation:
    """One AST node referencing a forbidden M10 symbol outside the allowed paths."""

    file: str
    line: int
    col: int
    symbol: str
    node_kind: str

    def render(self) -> str:
        return (
            f"  • {self.file}:{self.line}:{self.col}  "
            f"{self.symbol!r} ({self.node_kind})"
        )


def _repo_root(start: Path | None = None) -> Path:
    if start is not None:
        return start.resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "app").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError(
        "Could not locate backend/ root. Pass --root <backend-dir> explicitly."
    )


def _is_path_allowlisted(rel_path: str) -> bool:
    """True iff the relative POSIX path falls under an allowlisted subtree."""
    return any(rel_path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


def _iter_python_files(repo_root: Path) -> list[Path]:
    """Every .py file under backend/app/ excluding __pycache__."""
    app_dir = repo_root / "app"
    return sorted(
        p for p in app_dir.rglob("*.py")
        if "__pycache__" not in p.parts
    )


def _scan_file(path: Path, rel_path: str) -> list[Violation]:
    """Walk the AST of one .py file, return forbidden-symbol violations.

    The walker covers four node kinds:

    * :class:`ast.Name`       — variable reference (``meesho_column_header``)
    * :class:`ast.Attribute`  — attribute access (``obj.meesho_column_header``)
    * :class:`ast.keyword`    — call kwarg (``f(meesho_column_header=...)``)
    * :class:`ast.arg`        — function parameter (``def f(meesho_column_header):``)

    Plus :class:`ast.AnnAssign` / :class:`ast.Assign` where the LHS is a
    :class:`ast.Name` (e.g. ``meesho_column_header: str = "..."``).

    String literals (``ast.Constant`` with ``value: str``) are NOT walked —
    docstrings and JSON-shape examples are out of scope per §19.C posture.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover — defensive
        return []

    out: list[Violation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_SYMBOLS:
            out.append(Violation(
                file=rel_path,
                line=node.lineno,
                col=node.col_offset,
                symbol=node.id,
                node_kind="ast.Name",
            ))
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_SYMBOLS:
            out.append(Violation(
                file=rel_path,
                line=node.lineno,
                col=node.col_offset,
                symbol=node.attr,
                node_kind="ast.Attribute",
            ))
        elif isinstance(node, ast.keyword) and node.arg in FORBIDDEN_SYMBOLS:
            # ast.keyword does not carry lineno; use the enclosing call's
            # value position (best-effort).
            out.append(Violation(
                file=rel_path,
                line=getattr(node.value, "lineno", 0),
                col=getattr(node.value, "col_offset", 0),
                symbol=node.arg or "",
                node_kind="ast.keyword",
            ))
        elif isinstance(node, ast.arg) and node.arg in FORBIDDEN_SYMBOLS:
            out.append(Violation(
                file=rel_path,
                line=node.lineno,
                col=node.col_offset,
                symbol=node.arg,
                node_kind="ast.arg",
            ))

    return out


def scan(repo_root: Path | None = None) -> list[Violation]:
    """Walk all .py files under app/, return list of forbidden-symbol violations.

    Empty list = PASS. Non-empty list = FAIL.
    """
    root = _repo_root(repo_root)
    violations: list[Violation] = []

    for path in _iter_python_files(root):
        rel = path.relative_to(root).as_posix()
        if _is_path_allowlisted(rel):
            continue
        violations.extend(_scan_file(path, rel))

    return violations


def main(argv: list[str] | None = None) -> int:
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
            "§19.C Contract 9 PASS — no M10 forbidden symbol "
            f"({', '.join(sorted(FORBIDDEN_SYMBOLS))}) "
            "appears outside `app/modules/export/` + `app/adapters/gcs.py`."
        )
        return 0

    print(
        f"§19.C Contract 9 FAIL — {len(violations)} forbidden-symbol "
        "reference(s) found outside the allowlisted export + gcs subtrees:",
        file=sys.stderr,
    )
    for v in violations:
        print(v.render(), file=sys.stderr)
    print(
        "\nRemediation: move the symbol back into `app/modules/export/` (the "
        "M10 boundary per §14.J + §0.H) OR amend §14.J to widen the "
        "allowlist (requires master ratification).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
