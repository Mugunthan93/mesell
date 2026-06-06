"""Tests for :mod:`app.ai_ops.guardrail` — §6A.E Layers 1 + 2.

Covers:

* Layer 1: per-workload prefix injected correctly; enum block appended
  for autofill when allowed_enums supplied; never appended for the
  other two workloads.
* Layer 2 smart_picker: shape valid; invalid JSON → None; missing
  category_id / confidence out-of-range / non-list reasons → None.
* Layer 2 autofill: shape valid with enum match; out-of-allowlist value
  → None; free-text field accepted without allowlist.
* Layer 2 watermark: shape valid; non-bool has_watermark → None;
  confidence out-of-range → None.
* :func:`build_retry_prompt` includes the original prompt and names the
  violation.
"""

from __future__ import annotations

import json

from app.ai_ops import guardrail


# ── Layer 1 — apply_prompt_constraint ──────────────────────────────────────
class TestLayer1Prefix:
    def test_smart_picker_prefix_injected(self) -> None:
        out = guardrail.apply_prompt_constraint("BODY", "smart_picker")
        assert out.endswith("BODY")
        assert "JSON" in out
        assert "suggestions" in out
        assert "BODY" in out

    def test_autofill_prefix_injected(self) -> None:
        out = guardrail.apply_prompt_constraint("BODY", "autofill")
        assert "fields" in out
        assert "allowed enum list" in out.lower()
        assert out.endswith("BODY")

    def test_watermark_prefix_injected(self) -> None:
        out = guardrail.apply_prompt_constraint("BODY", "watermark")
        assert "has_watermark" in out
        assert out.endswith("BODY")

    def test_autofill_enum_block_appended_when_allowlist_supplied(self) -> None:
        out = guardrail.apply_prompt_constraint(
            "BODY",
            "autofill",
            allowed_enums={"color": ["red", "blue"], "size": ["S", "M", "L"]},
        )
        assert "Allowed enums per field" in out
        assert "color" in out
        assert "size" in out

    def test_autofill_no_enum_block_when_allowlist_empty(self) -> None:
        out = guardrail.apply_prompt_constraint("BODY", "autofill", allowed_enums={})
        assert "Allowed enums per field" not in out

    def test_smart_picker_ignores_allowed_enums(self) -> None:
        # smart_picker has no enum constraints; passing allowed_enums must
        # NOT append an enum block.
        out = guardrail.apply_prompt_constraint(
            "BODY", "smart_picker", allowed_enums={"color": ["red"]}
        )
        assert "Allowed enums per field" not in out


# ── Layer 2 — parse_and_validate ───────────────────────────────────────────
class TestLayer2SmartPicker:
    def _good(self) -> str:
        return json.dumps(
            {
                "suggestions": [
                    {
                        "category_id": "cat-1",
                        "confidence": 0.9,
                        "reasons": ["good fit"],
                    }
                ]
            }
        )

    def test_valid_shape_returns_parsed(self) -> None:
        out = guardrail.parse_and_validate(self._good(), "smart_picker")
        assert out is not None
        assert out["suggestions"][0]["category_id"] == "cat-1"

    def test_invalid_json_returns_none(self) -> None:
        assert guardrail.parse_and_validate("not json", "smart_picker") is None

    def test_top_level_list_returns_none(self) -> None:
        assert guardrail.parse_and_validate("[]", "smart_picker") is None

    def test_missing_suggestions_returns_none(self) -> None:
        assert guardrail.parse_and_validate("{}", "smart_picker") is None

    def test_missing_category_id_returns_none(self) -> None:
        text = json.dumps(
            {"suggestions": [{"confidence": 0.9, "reasons": ["x"]}]}
        )
        assert guardrail.parse_and_validate(text, "smart_picker") is None

    def test_confidence_above_1_returns_none(self) -> None:
        text = json.dumps(
            {
                "suggestions": [
                    {"category_id": "x", "confidence": 1.5, "reasons": []}
                ]
            }
        )
        assert guardrail.parse_and_validate(text, "smart_picker") is None

    def test_reasons_not_list_of_str_returns_none(self) -> None:
        text = json.dumps(
            {
                "suggestions": [
                    {"category_id": "x", "confidence": 0.5, "reasons": [1, 2]}
                ]
            }
        )
        assert guardrail.parse_and_validate(text, "smart_picker") is None


class TestLayer2Autofill:
    def test_enum_match_valid(self) -> None:
        text = json.dumps({"fields": {"color": "red"}})
        out = guardrail.parse_and_validate(
            text, "autofill", allowed_enums={"color": ["red", "blue"]}
        )
        assert out is not None
        assert out["fields"]["color"] == "red"

    def test_enum_violation_returns_none(self) -> None:
        text = json.dumps({"fields": {"color": "magenta"}})
        out = guardrail.parse_and_validate(
            text, "autofill", allowed_enums={"color": ["red", "blue"]}
        )
        assert out is None

    def test_free_text_field_accepted_without_allowlist(self) -> None:
        text = json.dumps({"fields": {"description": "A nice product"}})
        out = guardrail.parse_and_validate(
            text, "autofill", allowed_enums={}
        )
        assert out is not None

    def test_missing_fields_returns_none(self) -> None:
        assert (
            guardrail.parse_and_validate("{}", "autofill", allowed_enums={})
            is None
        )

    def test_invalid_value_type_returns_none(self) -> None:
        # value is a nested dict for a free-text field → reject.
        text = json.dumps({"fields": {"x": {"nested": "object"}}})
        out = guardrail.parse_and_validate(text, "autofill", allowed_enums={})
        assert out is None


class TestLayer2Watermark:
    def test_valid_shape(self) -> None:
        out = guardrail.parse_and_validate(
            json.dumps({"has_watermark": True, "confidence": 0.7}),
            "watermark",
        )
        assert out is not None
        assert out["has_watermark"] is True

    def test_non_bool_returns_none(self) -> None:
        out = guardrail.parse_and_validate(
            json.dumps({"has_watermark": "yes", "confidence": 0.7}),
            "watermark",
        )
        assert out is None

    def test_confidence_out_of_range_returns_none(self) -> None:
        out = guardrail.parse_and_validate(
            json.dumps({"has_watermark": False, "confidence": 1.7}),
            "watermark",
        )
        assert out is None


# ── build_retry_prompt ─────────────────────────────────────────────────────
class TestBuildRetryPrompt:
    def test_includes_original_prompt(self) -> None:
        out = guardrail.build_retry_prompt(
            "ORIGINAL PROMPT",
            "autofill",
            "BAD LLM OUTPUT",
            allowed_enums={"color": ["red"]},
        )
        assert "ORIGINAL PROMPT" in out

    def test_includes_failure_marker(self) -> None:
        out = guardrail.build_retry_prompt(
            "ORIG", "smart_picker", "junk", allowed_enums=None
        )
        assert "PREVIOUS ATTEMPT FAILED" in out
