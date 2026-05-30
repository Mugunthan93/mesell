"""Gemini engine — prompt building + response parsing (no live API calls)."""

import json
from unittest.mock import patch

import pytest

from app.services.ai_engine import (
    GeminiEngine,
    VARIATION_HINTS,
    _parse_response,
    _strip_fences,
)

# ---------------------------------------------------------------------------
# Helpers for mocking the Gemini SDK response shape used in regression tests.
# ---------------------------------------------------------------------------

def _make_candidate(finish_reason: int):
    """Return a minimal candidate object with the given finish_reason."""
    return type("Candidate", (), {"finish_reason": finish_reason})()


def _make_response(text: str, finish_reason: int = 1):
    """
    Build a minimal fake google.generativeai response.
    finish_reason 1 = STOP (normal), 2 = MAX_TOKENS (truncated).
    """
    candidate = _make_candidate(finish_reason)
    return type("Response", (), {"text": text, "candidates": [candidate]})()


def test_strip_fences_removes_json_block():
    raw = "```json\n{\"a\":1}\n```"
    assert _strip_fences(raw) == '{"a":1}'


def test_strip_fences_handles_plain_text():
    assert _strip_fences("  { } ") == "{ }"


def test_parse_response_handles_fenced_json():
    raw = '```json\n{"title":"T","description":"D","keywords":"k","category":"C","attributes":{}}\n```'
    parsed = _parse_response(raw)
    assert parsed["title"] == "T"


def test_parse_response_extracts_json_from_prose():
    raw = 'Here is the listing: {"title":"T","description":"D","keywords":"k","category":"C","attributes":{}} thanks!'
    parsed = _parse_response(raw)
    assert parsed["category"] == "C"


def test_parse_response_raises_on_garbage():
    with pytest.raises(ValueError):
        _parse_response("no json anywhere")


def test_parse_response_raises_on_truncated_json_no_closing_brace():
    """
    Regression test for the MAX_TOKENS truncation bug.

    When max_output_tokens was 1024, Gemini returned only ~97 chars — a
    fragment like:
        {
          "title": "Warm Woolen Saree for Casual Wear ...",
          "description
    — with no closing brace.  Both json.loads and the ``{.*}`` regex failed,
    producing the misleading "No JSON object found" error.  The regex is
    correct; the real fix is raising a clear error before JSON parsing when
    the response is an incomplete fragment, and bumping max_output_tokens.
    """
    truncated = (
        '{\n'
        '  "title": "Warm Woolen Saree for Casual Wear - Elegant Red Wool '
        'Saree with Blouse Piece for Women",\n'
        '  "description'
        # deliberately ends here — no closing quote, no closing brace
    )
    with pytest.raises((ValueError, json.JSONDecodeError)):
        _parse_response(truncated)


def test_build_prompt_substitutes_all_placeholders():
    prompt = GeminiEngine._build_prompt(
        product_name="Cotton Kurti",
        category="Kurtis",
        subcategory=None,
        material="Cotton",
        sizes="S, M, L",
        colors="red",
        price=599,
        image_description=None,
        notes=None,
        variation_hint=VARIATION_HINTS[0],
    )
    # All template variables must be filled in.
    assert "{product_name}" not in prompt
    assert "{required_attributes}" not in prompt
    assert "Cotton Kurti" in prompt
    assert "Lead with the fabric" in prompt  # variation hint sneaked in


def test_build_prompt_falls_back_to_default_attributes_for_unknown_category():
    prompt = GeminiEngine._build_prompt(
        product_name="X",
        category="No Such Category",
        subcategory=None,
        material=None,
        sizes=None,
        colors=None,
        price=None,
        image_description=None,
        notes=None,
        variation_hint=VARIATION_HINTS[0],
    )
    # _default config has at least color + material in required.
    assert "color" in prompt
    assert "material" in prompt


@pytest.mark.asyncio
async def test_generate_listing_normalises_response():
    """The engine must trim title, lower-case keywords, and accept dict attributes."""

    payload = {
        "title": "    TRENDY COTTON KURTI ".ljust(220, " "),
        "description": "  Soft cotton kurti for daily wear.  ",
        "keywords": "KURTI, Cotton, Women",
        "category": "Kurtis",
        "attributes": {"fabric": "cotton blend"},
    }

    class FakeModel:
        def generate_content(self, prompt, **_):  # noqa: D401
            return _make_response(json.dumps(payload))

    engine = GeminiEngine(api_key="dummy")
    with patch.object(engine, "_get_model", return_value=FakeModel()):
        out = await engine.generate_listing(
            product_name="Cotton Kurti",
            category="Kurtis",
            material="Cotton",
            sizes="S,M,L",
            colors="red",
            price=599,
        )

    assert len(out["title"]) <= 200
    assert out["keywords"] == "kurti, cotton, women"
    assert out["attributes"] == {"fabric": "cotton blend"}


@pytest.mark.asyncio
async def test_generate_listing_raises_when_keys_missing():
    incomplete = {"title": "T", "description": "D"}

    class FakeModel:
        def generate_content(self, *_a, **_k):
            return _make_response(json.dumps(incomplete))

    engine = GeminiEngine(api_key="dummy")
    with patch.object(engine, "_get_model", return_value=FakeModel()):
        with pytest.raises(ValueError, match="missing keys"):
            await engine.generate_listing(product_name="X", category="Kurtis")


@pytest.mark.asyncio
async def test_generate_listing_raises_on_max_tokens_truncation():
    """
    Regression: finish_reason=2 (MAX_TOKENS) must raise ValueError with a
    clear 'truncated' message before the JSON parser is even invoked.

    This is the scenario that caused the original 'No JSON object found'
    error — a 97-char fragment starting with a partial title field, produced
    by Gemini when max_output_tokens was 1024 and the response needed ~400
    output tokens.
    """
    truncated_text = (
        '{\n  "title": "Warm Woolen Saree for Casual Wear - Elegant Red Wool '
        'Saree with Blouse Piece for Women",\n  "description'
    )

    class FakeModel:
        def generate_content(self, *_a, **_k):
            # finish_reason 2 == MAX_TOKENS
            return _make_response(truncated_text, finish_reason=2)

    engine = GeminiEngine(api_key="dummy")
    with patch.object(engine, "_get_model", return_value=FakeModel()):
        with pytest.raises(ValueError, match="truncated"):
            await engine.generate_listing(
                product_name="Warm Woolen Saree",
                category="Sarees",
                material="Wool",
                colors="Red",
                price=799,
            )


@pytest.mark.asyncio
async def test_generate_listing_uses_2048_max_output_tokens():
    """
    Verify the generation config has been bumped to 2048 max_output_tokens.
    A complete catalog JSON is ~400-600 tokens; 1024 was insufficient.
    """
    captured: list[dict] = []

    class FakeModel:
        def generate_content(self, prompt, generation_config=None, **_):
            if generation_config:
                captured.append(generation_config)
            payload = {
                "title": "Test Saree",
                "description": "A test saree.",
                "keywords": "test, saree",
                "category": "Sarees",
                "attributes": {"color": "red"},
            }
            return _make_response(json.dumps(payload))

    engine = GeminiEngine(api_key="dummy")
    with patch.object(engine, "_get_model", return_value=FakeModel()):
        await engine.generate_listing(product_name="Test Saree", category="Sarees")

    assert captured, "generate_content was never called with generation_config"
    assert captured[0]["max_output_tokens"] == 2048, (
        f"Expected max_output_tokens=2048, got {captured[0]['max_output_tokens']}"
    )
