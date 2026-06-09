"""§19.C Contract 9 — pytest wrapper for M10 forbidden-symbol AST scanner.

Two assertions per the §19 construction protocol:

1. **Happy path** — :func:`check_no_meesho_symbols_outside_export.scan`
   returns an empty list against the live codebase.
2. **Counter-example** — a synthetic ``catalog/service.py`` containing a
   reference to ``meesho_column_header`` MUST be flagged by the scanner.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tests.lint import check_no_meesho_symbols_outside_export as scanner


@pytest.mark.smoke
def test_no_meesho_symbols_clean_on_live_codebase() -> None:
    """No M10 forbidden symbol appears as an identifier outside export + gcs.

    Docstring/string-literal mentions are intentionally NOT flagged per the
    L_export_M10_AST_scanner spec line 38 ("walking name resolution + attribute
    access is the actual M10 check"). KNOWN_DOCSTRING_HITS documents the
    pre-existing string-literal hits for forward-compat.
    """
    violations = scanner.scan()
    assert violations == [], (
        "§19.C Contract 9 FAIL on live codebase:\n"
        + "\n".join(v.render() for v in violations)
    )


def test_no_meesho_symbols_flags_attribute_in_catalog(tmp_path: Path) -> None:
    """A synthetic ``catalog/service.py`` referencing a forbidden symbol trips.

    The counter-example uses the symbol as an attribute access
    (``spec.meesho_column_header``) — the spec line "walking name resolution
    + attribute access is the actual M10 check" is the exact case exercised.
    """
    fake_app = tmp_path / "app" / "modules" / "catalog"
    fake_app.mkdir(parents=True)
    fake_tests = tmp_path / "tests"
    fake_tests.mkdir(parents=True)

    (fake_app / "service.py").write_text(textwrap.dedent('''\
        """Synthetic counter-example for §19.C Contract 9."""


        def emit(spec):
            """Reference forbidden M10 symbol via attribute access."""
            return spec.meesho_column_header
        '''))

    violations = scanner.scan(repo_root=tmp_path)
    assert any(
        v.file == "app/modules/catalog/service.py"
        and v.symbol == "meesho_column_header"
        and v.node_kind == "ast.Attribute"
        for v in violations
    ), (
        "§19.C Contract 9 counter-example failed to flag attribute access "
        "to `meesho_column_header` in `catalog/service.py`. Violations:\n"
        + "\n".join(v.render() for v in violations)
    )


def test_no_meesho_symbols_flags_keyword_in_image(tmp_path: Path) -> None:
    """A synthetic ``image/repository.py`` passing a forbidden keyword trips.

    Exercises the :class:`ast.keyword` arm of the walker — the kwarg
    ``enum_codes_map=...`` in a function call is identified.
    """
    fake_app = tmp_path / "app" / "modules" / "image"
    fake_app.mkdir(parents=True)
    fake_tests = tmp_path / "tests"
    fake_tests.mkdir(parents=True)

    (fake_app / "repository.py").write_text(textwrap.dedent('''\
        """Synthetic counter-example — keyword argument."""


        def fake_factory():
            return None


        def call_site():
            return fake_factory(enum_codes_map={"a": "b"})
        '''))

    violations = scanner.scan(repo_root=tmp_path)
    assert any(
        v.symbol == "enum_codes_map" and v.node_kind == "ast.keyword"
        for v in violations
    ), (
        "§19.C Contract 9 counter-example failed to flag keyword argument "
        "`enum_codes_map=...`. Violations:\n"
        + "\n".join(v.render() for v in violations)
    )


def test_no_meesho_symbols_allowlists_export_subtree(tmp_path: Path) -> None:
    """A reference INSIDE ``app/modules/export/`` MUST NOT be flagged.

    Mirrors the live ``export/service.py`` shape and confirms the path-prefix
    allowlist short-circuits the AST walk.
    """
    fake_export = tmp_path / "app" / "modules" / "export"
    fake_export.mkdir(parents=True)
    fake_tests = tmp_path / "tests"
    fake_tests.mkdir(parents=True)

    (fake_export / "service.py").write_text(textwrap.dedent('''\
        """Legitimate export-internal use of M10 symbol."""


        def emit(spec):
            return spec.meesho_column_header  # allowlisted by path prefix
        '''))

    violations = scanner.scan(repo_root=tmp_path)
    assert violations == [], (
        "§19.C Contract 9 allowlist failed — export-internal reference "
        "to `meesho_column_header` was flagged. Violations:\n"
        + "\n".join(v.render() for v in violations)
    )


def test_no_meesho_symbols_skips_docstring_string_literal(tmp_path: Path) -> None:
    """A string literal mentioning the symbol MUST NOT be flagged.

    Mirrors the live ``shared/models/template.py`` docstring shape — the
    walker intentionally ignores ``ast.Constant`` nodes per the spec.
    """
    fake_shared = tmp_path / "app" / "shared" / "models"
    fake_shared.mkdir(parents=True)
    fake_tests = tmp_path / "tests"
    fake_tests.mkdir(parents=True)

    (fake_shared / "template.py").write_text(textwrap.dedent('''\
        """JSON-shape example as a docstring.

        Sample:
            "meesho_column_header": "...",
            "meesho_column_index": N,
            "enum_codes_map": null,
        """
        '''))

    violations = scanner.scan(repo_root=tmp_path)
    assert violations == [], (
        "§19.C Contract 9 false positive — docstring string-literal mention "
        "of `meesho_column_header` was flagged as identifier. Violations:\n"
        + "\n".join(v.render() for v in violations)
    )


def test_known_docstring_hits_are_documented() -> None:
    """Every KNOWN_DOCSTRING_HITS entry MUST be a 3-tuple of correct shape.

    Defensive — catches accidental typos that would silently desync the
    forward-compat documentation from the architecture spec.
    """
    for entry in scanner.KNOWN_DOCSTRING_HITS:
        path, line, symbol = entry
        assert isinstance(path, str) and path.endswith(".py"), entry
        assert isinstance(line, int) and line >= 0, entry
        assert symbol in scanner.FORBIDDEN_SYMBOLS, entry
