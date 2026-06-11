"""§19.C Contract 8 — pytest wrapper for ``scope_to_user`` AST scanner.

Two assertions per the §19 construction protocol:

1. **Happy path** — :func:`check_scope_to_user.scan` returns an empty list
   against the live ``backend/app/modules/*/repository.py`` files.
2. **Counter-example** — a synthetic ``repository.py`` with a public method
   that lacks ``user_id`` MUST be flagged by the scanner.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from tests.lint import check_scope_to_user as scanner


@pytest.mark.smoke
def test_scope_to_user_clean_on_live_codebase() -> None:
    """No public repository method on owned-table modules is missing ``user_id``.

    The :data:`KNOWN_DEVIATIONS` allowlist covers pre-existing deviations that
    enforce tenancy upstream at the service layer. A NEW violation surfacing
    here is a §15.B breach — fix the signature OR amend KNOWN_DEVIATIONS with
    an upstream-gate citation.
    """
    violations = scanner.scan()
    assert violations == [], (
        "§19.C Contract 8 FAIL on live codebase:\n"
        + "\n".join(v.render() for v in violations)
    )


def test_scope_to_user_flags_counter_example(tmp_path: Path) -> None:
    """A synthetic public repository method without ``user_id`` MUST trip.

    Builds a fake backend/app/modules/catalog/repository.py with one public
    function whose signature omits ``user_id``, runs the scanner against that
    synthetic root, and asserts at least one violation surfaces.
    """
    # Mirror the minimum layout the scanner expects.
    fake_app = tmp_path / "app" / "modules"
    fake_tests = tmp_path / "tests"  # _repo_root checks for `tests/` sibling
    fake_tests.mkdir(parents=True)

    # Counter-example: catalog/repository.py without user_id on a public method.
    catalog_repo = fake_app / "catalog" / "repository.py"
    catalog_repo.parent.mkdir(parents=True)
    catalog_repo.write_text(textwrap.dedent('''\
        """Synthetic counter-example for §19.C Contract 8."""
        from uuid import UUID


        async def find_by_id(db, product_id: UUID):
            """Public method WITHOUT user_id — must be flagged."""
            return None


        async def _private_helper(db, product_id: UUID):
            """Private helper — NOT flagged (leading underscore)."""
            return None
        '''))

    # Stub the other 4 scanned modules so the scanner reports them as missing
    # only if we leave them off — we want a clean test against catalog only,
    # so create empty repository.py files for the rest.
    for module in ("customer", "image", "pricing", "export"):
        path = fake_app / module / "repository.py"
        path.parent.mkdir(parents=True)
        path.write_text("# minimal placeholder — no public methods.\n")

    violations = scanner.scan(repo_root=tmp_path)

    # The synthetic catalog.find_by_id MUST be flagged.
    assert any(
        v.qualname == "app.modules.catalog.repository.find_by_id"
        and "user_id" in v.reason
        for v in violations
    ), (
        "§19.C Contract 8 counter-example failed to flag "
        "`catalog.repository.find_by_id` missing `user_id`. "
        "Violations were:\n"
        + "\n".join(v.render() for v in violations)
    )

    # The private helper MUST NOT be flagged.
    assert not any(
        v.qualname.endswith("._private_helper")
        for v in violations
    ), (
        "§19.C Contract 8 false positive: private helper was flagged. "
        "Violations were:\n"
        + "\n".join(v.render() for v in violations)
    )


def test_scope_to_user_allowlists_known_deviation(tmp_path: Path) -> None:
    """A method in :data:`KNOWN_DEVIATIONS` MUST NOT be flagged.

    Mirrors the live ``pricing.repository.insert_calc`` shape (no ``user_id``,
    has ``product_id``) and asserts the scanner respects the allowlist.
    """
    fake_app = tmp_path / "app" / "modules"
    fake_tests = tmp_path / "tests"
    fake_tests.mkdir(parents=True)

    # Mirror pricing.repository.insert_calc shape.
    pricing_repo = fake_app / "pricing" / "repository.py"
    pricing_repo.parent.mkdir(parents=True)
    pricing_repo.write_text(textwrap.dedent('''\
        """Synthetic — exercises KNOWN_DEVIATIONS allowlist."""
        from uuid import UUID


        async def insert_calc(db, *, product_id: UUID):
            """Allowlisted: tenancy upstream per docstring."""
            return None


        async def find_latest_by_product(db, user_id: UUID, product_id: UUID):
            """Non-allowlisted method with user_id — clean."""
            return None
        '''))
    # Stubs for the other 4 scanned modules.
    for module in ("customer", "catalog", "image", "export"):
        path = fake_app / module / "repository.py"
        path.parent.mkdir(parents=True)
        path.write_text("# empty placeholder.\n")

    violations = scanner.scan(repo_root=tmp_path)
    assert not any(v.qualname.endswith("insert_calc") for v in violations), (
        "§19.C Contract 8 KNOWN_DEVIATIONS allowlist failed — "
        "`pricing.repository.insert_calc` was flagged despite being listed."
    )


def test_scope_to_user_known_deviations_documented() -> None:
    """Every KNOWN_DEVIATIONS entry MUST be qualname-shaped.

    Defensive: catches accidental typos that would silently widen the
    allowlist past intent.
    """
    for entry in scanner.KNOWN_DEVIATIONS:
        parts = entry.split(".")
        assert len(parts) >= 4 and parts[0] == "app", (
            f"KNOWN_DEVIATIONS entry malformed: {entry!r}. "
            "Expected `app.modules.<m>.repository.<func>`."
        )
        assert parts[1] == "modules", entry
        assert parts[3] == "repository", entry
