"""Gemini-backed catalog text generation."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from app.config import settings
from app.data import get_category_config

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "data" / "prompts" / "catalog_generation.txt"

VARIATION_HINTS = [
    "Lead with the fabric and occasion in the title.",
    "Lead with the style/cut and target audience in the title.",
    "Lead with the festival/season relevance in the title.",
]


def _strip_fences(text: str) -> str:
    """Drop ```json ... ``` fences if Gemini snuck them in."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_response(text: str) -> dict:
    """Robustly pull a JSON object out of an LLM response."""
    cleaned = _strip_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in Gemini response")
        return json.loads(match.group(0))


class GeminiEngine:
    """Wraps google-generativeai with a single :meth:`generate_listing` call."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model or settings.GEMINI_MODEL
        self._model = None

    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai  # type: ignore

            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
        return self._model

    @staticmethod
    def _build_prompt(*, product_name: str, category: str | None, subcategory: str | None,
                      material: str | None, sizes: str | None, colors: str | None,
                      price: float | None, image_description: str | None,
                      notes: str | None, variation_hint: str) -> str:
        template = PROMPT_PATH.read_text()
        required = get_category_config(category or "_default")["required"]
        return template.format(
            product_name=product_name,
            category=category or "Unknown",
            subcategory=subcategory or "Unknown",
            material=material or "Unknown",
            sizes=sizes or "Unknown",
            colors=colors or "Unknown",
            price=price if price is not None else "Unknown",
            notes=notes or "—",
            image_description=image_description or "—",
            required_attributes=", ".join(required),
            variation_hint=variation_hint,
        )

    async def generate_listing(
        self,
        *,
        product_name: str,
        category: str | None = None,
        subcategory: str | None = None,
        material: str | None = None,
        sizes: str | None = None,
        colors: str | None = None,
        price: float | None = None,
        image_description: str | None = None,
        notes: str | None = None,
        variation_index: int = 0,
    ) -> dict:
        """Call Gemini and return ``{title, description, keywords, category, attributes}``."""
        prompt = self._build_prompt(
            product_name=product_name,
            category=category,
            subcategory=subcategory,
            material=material,
            sizes=sizes,
            colors=colors,
            price=price,
            image_description=image_description,
            notes=notes,
            variation_hint=VARIATION_HINTS[variation_index % len(VARIATION_HINTS)],
        )

        model = self._get_model()

        def _call() -> str:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    # 1024 was too low — a typical catalog JSON is 400-600 tokens.
                    # With prompt overhead (~430 tokens) the model was hitting
                    # MAX_TOKENS mid-response, producing truncated JSON with no
                    # closing brace.  2048 gives comfortable headroom and is still
                    # well within the model's context window.
                    "max_output_tokens": 2048,
                    "response_mime_type": "application/json",
                },
            )
            # Guard against MAX_TOKENS truncation (finish_reason == 2).
            # If the model was cut off, response.text will be incomplete JSON;
            # raise an explicit error rather than letting the JSON parser surface
            # a confusing "Expecting property name" message.
            try:
                candidates = response.candidates
                if candidates:
                    finish_reason = candidates[0].finish_reason
                    # finish_reason 2 == MAX_TOKENS in the google-generativeai SDK
                    if finish_reason == 2:
                        raise ValueError(
                            "Gemini response truncated by MAX_TOKENS limit; "
                            f"partial text (first 200 chars): {response.text[:200]!r}"
                        )
            except (AttributeError, IndexError):
                pass  # SDK version without candidates — proceed to JSON parse
            return response.text

        text = await asyncio.to_thread(_call)
        try:
            parsed = _parse_response(text)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error(f"Failed to parse Gemini response: {exc}\nraw: {text[:500]}")
            raise

        required_keys = {"title", "description", "keywords", "category", "attributes"}
        missing = required_keys - parsed.keys()
        if missing:
            raise ValueError(f"Gemini response missing keys: {missing}")

        # Defensive normalisation.
        parsed["title"] = str(parsed["title"]).strip()[:200]
        parsed["description"] = str(parsed["description"]).strip()
        parsed["keywords"] = str(parsed["keywords"]).strip().lower()
        if not isinstance(parsed["attributes"], dict):
            parsed["attributes"] = {}
        return parsed


_engine: GeminiEngine | None = None


def get_ai_engine() -> GeminiEngine:
    global _engine
    if _engine is None:
        _engine = GeminiEngine()
    return _engine
