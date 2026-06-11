"""Tests for :mod:`app.ai_ops.prompt_registry` — §6A.G.

Covers:

* :func:`resolve` returns the expected ``PromptTemplate`` for the 3
  active V1 prompt IDs.
* Each V1 prompt module declares the locked workload + rendered_by.
* Workload-mismatch between ``prompt_id`` and the ``workload`` arg
  raises :class:`PromptResolutionError`.
* Malformed prompt_id raises :class:`PromptResolutionError`.
* Unknown prompt module raises :class:`PromptResolutionError`.
* :func:`render` substitutes ``{{var}}`` placeholders; missing
  placeholders are left as-is.
"""

from __future__ import annotations

import pytest

from app.ai_ops import prompt_registry

pytestmark = pytest.mark.unit


# ── resolve() ──────────────────────────────────────────────────────────────
class TestResolveActiveVersions:
    @pytest.mark.parametrize(
        "prompt_id,workload,rendered_by",
        [
            ("smart_picker.v1", "smart_picker", "text"),
            ("autofill.v1", "autofill", "text"),
            ("watermark.v1", "watermark", "vision"),
        ],
    )
    def test_v1_active_versions(
        self, prompt_id: str, workload: str, rendered_by: str
    ) -> None:
        t = prompt_registry.resolve(prompt_id, workload)
        assert t.version == "v1"
        assert t.workload == workload
        assert t.rendered_by == rendered_by
        assert isinstance(t.template, str) and len(t.template) > 0


class TestResolveErrors:
    def test_workload_mismatch_raises(self) -> None:
        with pytest.raises(prompt_registry.PromptResolutionError):
            prompt_registry.resolve("smart_picker.v1", "autofill")

    def test_malformed_no_dot_raises(self) -> None:
        with pytest.raises(prompt_registry.PromptResolutionError):
            prompt_registry.resolve("smart_picker_v1", "smart_picker")

    def test_malformed_version_raises(self) -> None:
        with pytest.raises(prompt_registry.PromptResolutionError):
            prompt_registry.resolve("smart_picker.x1", "smart_picker")

    def test_unknown_module_raises(self) -> None:
        with pytest.raises(prompt_registry.PromptResolutionError):
            prompt_registry.resolve("nonexistent.v1", "smart_picker")


# ── render() ───────────────────────────────────────────────────────────────
class TestRender:
    def test_substitutes_placeholders(self) -> None:
        out = prompt_registry.render(
            "Hello {{name}}, the {{thing}}",
            {"name": "world", "thing": "test"},
        )
        assert out == "Hello world, the test"

    def test_missing_placeholder_left_as_is(self) -> None:
        out = prompt_registry.render(
            "Hello {{name}}, the {{thing}}", {"name": "world"}
        )
        assert "{{thing}}" in out

    def test_stringifies_non_str_values(self) -> None:
        out = prompt_registry.render("count={{n}}", {"n": 42})
        assert out == "count=42"

    def test_empty_vars_returns_template_verbatim(self) -> None:
        out = prompt_registry.render("static text", {})
        assert out == "static text"
