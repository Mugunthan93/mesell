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

    fake_response = type("R", (), {"text": json.dumps(payload)})

    class FakeModel:
        def generate_content(self, prompt, **_):  # noqa: D401
            return fake_response

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
    fake_response = type("R", (), {"text": json.dumps(incomplete)})

    class FakeModel:
        def generate_content(self, *_a, **_k):
            return fake_response

    engine = GeminiEngine(api_key="dummy")
    with patch.object(engine, "_get_model", return_value=FakeModel()):
        with pytest.raises(ValueError, match="missing keys"):
            await engine.generate_listing(product_name="X", category="Kurtis")
