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


def _fix_json(text: str) -> str:
    """Best-effort repair of common LLM JSON quirks.

    1. Trailing commas before } or ] (very common with Gemini).
    2. Truncated JSON — if there is no closing ``}`` we add enough to make the
       string parseable so the caller can at least extract partial data.
    """
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # If the response was cut off before the final closing brace, close it
    opens = text.count("{") - text.count("}")
    if opens > 0:
        # Strip any dangling incomplete key/value at the very end, then close
        text = re.sub(r',\s*"[^"]*$', "", text)   # drop partial last key
        text = re.sub(r',\s*$', "", text)          # drop trailing comma
        text += "}" * opens

    return text


def _parse_response(text: str) -> dict:
    """Robustly pull a JSON object out of an LLM response."""
    cleaned = _strip_fences(text)

    # First attempt — vanilla parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Second attempt — fix trailing commas / truncation then parse
    try:
        return json.loads(_fix_json(cleaned))
    except json.JSONDecodeError:
        pass

    # Third attempt — extract first {...} block then fix
    match = re.search(r"\{.*", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(_fix_json(match.group(0)))
        except json.JSONDecodeError:
            pass

    raise ValueError("No JSON object found in Gemini response")


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
                    "max_output_tokens": 2048,
                },
            )
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
