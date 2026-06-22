"""Prompt template direct render tests.

Wave: qa-image-ai (Wave A).

Closes §1.B partial-gaps for ``autofill_v1.py`` and ``watermark_v1.py``:
  - direct render + RENDERED_BY assertion for each template
  - confirms the prompt registry resolves them end-to-end
  - confirms variable substitution works for autofill

These are PURE unit tests — no DB, no network, no mocks beyond what the
prompt_registry resolver needs.
"""

from __future__ import annotations

import pytest

from app.ai_ops import prompt_registry
from app.ai_ops.prompts import autofill_v1, watermark_v1

pytestmark = pytest.mark.unit


# ===========================================================================
# autofill_v1 — direct render assertions
# ===========================================================================
class TestAutofillV1PromptTemplate:
    """Direct assertions on the autofill_v1 prompt template module."""

    def test_rendered_by_is_text(self) -> None:
        """autofill workload uses the text SDK path (not vision)."""
        assert autofill_v1.RENDERED_BY == "text"

    def test_workload_is_autofill(self) -> None:
        assert autofill_v1.WORKLOAD == "autofill"

    def test_template_contains_product_spec_placeholder(self) -> None:
        """autofill template must include {{product_spec}} variable."""
        assert "{{product_spec}}" in autofill_v1.TEMPLATE

    def test_template_contains_schema_placeholder(self) -> None:
        """autofill template must include {{schema}} variable."""
        assert "{{schema}}" in autofill_v1.TEMPLATE

    def test_registry_resolves_autofill_v1(self) -> None:
        """prompt_registry.resolve('autofill.v1', 'autofill') returns the template."""
        tmpl = prompt_registry.resolve("autofill.v1", "autofill")
        assert tmpl is not None
        assert tmpl.rendered_by == "text"

    def test_registry_render_substitutes_product_spec(self) -> None:
        """Variable substitution replaces {{product_spec}} in the rendered text."""
        tmpl = prompt_registry.resolve("autofill.v1", "autofill")
        rendered = prompt_registry.render(
            tmpl.template,
            {"product_spec": "Cotton kurti size M", "schema": "{}"},
        )
        assert "Cotton kurti size M" in rendered
        # The raw placeholder must be gone
        assert "{{product_spec}}" not in rendered

    def test_registry_render_substitutes_schema(self) -> None:
        """Variable substitution replaces {{schema}} in the rendered text."""
        tmpl = prompt_registry.resolve("autofill.v1", "autofill")
        schema_json = '{"fields": ["fabric"]}'
        rendered = prompt_registry.render(
            tmpl.template,
            {"product_spec": "test spec", "schema": schema_json},
        )
        assert schema_json in rendered
        assert "{{schema}}" not in rendered


# ===========================================================================
# watermark_v1 — direct render assertions
# ===========================================================================
class TestWatermarkV1PromptTemplate:
    """Direct assertions on the watermark_v1 prompt template module."""

    def test_rendered_by_is_vision(self) -> None:
        """watermark workload uses the vision SDK path (not text)."""
        assert watermark_v1.RENDERED_BY == "vision"

    def test_workload_is_watermark(self) -> None:
        assert watermark_v1.WORKLOAD == "watermark"

    def test_template_is_non_empty(self) -> None:
        assert len(watermark_v1.TEMPLATE.strip()) > 0

    def test_template_contains_watermark_instruction(self) -> None:
        """Template must describe what constitutes a watermark."""
        assert "watermark" in watermark_v1.TEMPLATE.lower()

    def test_template_contains_json_output_instruction(self) -> None:
        """Template must instruct JSON output with has_watermark key."""
        assert "has_watermark" in watermark_v1.TEMPLATE

    def test_registry_resolves_watermark_v1(self) -> None:
        """prompt_registry.resolve('watermark.v1', 'watermark') returns the template."""
        tmpl = prompt_registry.resolve("watermark.v1", "watermark")
        assert tmpl is not None
        assert tmpl.rendered_by == "vision"

    def test_watermark_template_has_no_variables(self) -> None:
        """watermark.v1 has no {{var}} placeholders — image bytes are passed directly."""
        tmpl = prompt_registry.resolve("watermark.v1", "watermark")
        # Render with empty vars should not raise or leave placeholders
        rendered = prompt_registry.render(tmpl.template, {})
        # No unresolved {{...}} patterns
        assert "{{" not in rendered
