"""Unit tests for the audit-mw autosave coalescing match logic (G5).

The catalog-form plan's REAL autosave surface is bare
``PATCH /api/v1/products/{id}`` (FEATURE_PLAN.md §F3 + audit §4.G).  The
original ``_AUTOSAVE_PATH`` regex only matched the explicit-suffix
``/products/{id}/(draft|autosave)`` forms, so coalescing never fired for the
real path.  ``_is_autosave(method, path)`` widens the match to include bare
``PATCH /products/{id}`` while keeping the explicit-suffix paths AND refusing
to coalesce PUT/POST/DELETE (so a delete-product never silently coalesces).

Pure-function tests — no Valkey, no DB.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.middleware.audit_mw import _AUTOSAVE_PATH, _is_autosave

pytestmark = pytest.mark.unit

_PID = str(uuid4())
_BARE = f"/api/v1/products/{_PID}"
_DRAFT = f"/api/v1/products/{_PID}/draft"
_AUTOSAVE = f"/api/v1/products/{_PID}/autosave"


class TestBarePatchCoalesces:
    def test_patch_bare_product_path_coalesces(self) -> None:
        """The real autosave surface — PATCH /products/{id} — now coalesces."""
        assert _is_autosave("PATCH", _BARE) is True

    def test_patch_bare_product_path_trailing_slash(self) -> None:
        assert _is_autosave("PATCH", _BARE + "/") is True


class TestExplicitSuffixStillCoalesces:
    @pytest.mark.parametrize("path", [_DRAFT, _AUTOSAVE])
    @pytest.mark.parametrize("method", ["PATCH", "PUT", "POST"])
    def test_draft_and_autosave_paths_still_coalesce_for_writes(
        self, method: str, path: str
    ) -> None:
        """Explicit-suffix autosave paths coalesce for any write method
        (the regex was already method-agnostic for these — preserved)."""
        assert _is_autosave(method, path) is True

    def test_underlying_regex_still_matches_suffix_paths(self) -> None:
        """Belt-and-braces — the named regex itself is unchanged for suffixes."""
        assert _AUTOSAVE_PATH.match(_DRAFT) is not None
        assert _AUTOSAVE_PATH.match(_AUTOSAVE) is not None
        assert _AUTOSAVE_PATH.match(_BARE) is None


class TestNonAutosaveWritesDoNotCoalesce:
    @pytest.mark.parametrize("method", ["PUT", "POST", "DELETE"])
    def test_bare_product_path_non_patch_does_not_coalesce(self, method: str) -> None:
        """PUT/POST/DELETE on the bare product path must NOT coalesce — e.g.
        DELETE /products/{id} (delete-product) is a discrete, audited event."""
        assert _is_autosave(method, _BARE) is False

    def test_post_create_product_collection_does_not_coalesce(self) -> None:
        """POST /products (collection create) is not an autosave."""
        assert _is_autosave("POST", "/api/v1/products") is False

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/products",
            f"/api/v1/products/{_PID}/images",
            f"/api/v1/products/{_PID}/autofill",
            f"/api/v1/products/{_PID}/price-calc",
            f"/api/v1/products/{_PID}/export-xlsx",
            "/api/v1/categories/suggest",
            "/api/v1/seller-profile",
        ],
    )
    def test_other_product_subpaths_do_not_coalesce_even_for_patch(
        self, path: str
    ) -> None:
        """Sub-resources (images/autofill/price-calc/export) and unrelated
        routes never match — only the bare product path or draft/autosave do."""
        assert _is_autosave("PATCH", path) is False

    def test_case_insensitive_method_for_bare_patch(self) -> None:
        """Method comparison is case-insensitive for the bare-path branch."""
        assert _is_autosave("patch", _BARE) is True
