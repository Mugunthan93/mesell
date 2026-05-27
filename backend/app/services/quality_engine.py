"""QualityGate — 9 validation rules with weighted scoring.

Each rule returns ``(status, detail, fix?)`` where ``status`` is
``pass``/``warn``/``fail``. Rule metadata lives in :data:`RULES`. The overall
score is the sum of awarded weights divided by total weight, on a 0-100 scale.
A catalog passes iff ``score >= PASS_SCORE_THRESHOLD`` **and** no
``severity="fail"`` rule failed.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data import all_banned_words, get_category_config, is_valid_category
from app.models.catalog import Catalog
from app.models.image import Image
from app.models.sku import SKU
from app.schemas.quality import QualityCheckResult, QualityReport

logger = logging.getLogger(__name__)

PASS_SCORE_THRESHOLD = 70

MIN_DIMENSION = 1024
WHITE_BG_MIN_RATIO = 0.6
TITLE_MIN = 30
TITLE_MAX = 200
KEYWORD_HINT_MIN = 4


@dataclass
class Rule:
    name: str
    severity: str  # "fail" or "warn"
    weight: int


RULES: list[Rule] = [
    Rule("image_size",        "fail", 12),
    Rule("white_bg",          "warn", 10),
    Rule("watermark",         "fail", 12),
    Rule("title_length",      "fail", 10),
    Rule("title_keywords",    "warn", 8),
    Rule("required_attributes", "fail", 15),
    Rule("banned_words",      "fail", 13),
    Rule("duplicate_check",   "warn", 10),
    Rule("category_mapping",  "fail", 10),
]


class QualityEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._banned = set(all_banned_words())

    async def validate_catalog(self, catalog_id: uuid.UUID) -> QualityReport:
        catalog = (
            await self.db.execute(
                select(Catalog)
                .where(Catalog.id == catalog_id)
                .options(selectinload(Catalog.skus).selectinload(SKU.images))
            )
        ).scalar_one_or_none()
        if catalog is None:
            raise ValueError(f"Catalog {catalog_id} not found")

        skus = list(catalog.skus)
        results: list[QualityCheckResult] = []

        for rule in RULES:
            checker: Callable = getattr(self, f"_check_{rule.name}")
            status, detail, fix = await checker(catalog, skus)
            awarded = rule.weight if status == "pass" else 0
            results.append(
                QualityCheckResult(
                    name=rule.name,
                    status=status,
                    severity=rule.severity,
                    weight=rule.weight,
                    score=awarded,
                    detail=detail,
                    fix=fix,
                )
            )

        total_weight = sum(r.weight for r in RULES)
        awarded = sum(r.score for r in results)
        score = round((awarded / total_weight) * 100) if total_weight else 0
        had_fail = any(r.status == "fail" and r.severity == "fail" for r in results)
        passed = (score >= PASS_SCORE_THRESHOLD) and not had_fail

        if catalog.skus:
            catalog.quality_score = score
            for sku in catalog.skus:
                sku.quality_score = score
                sku.quality_checks = {r.name: r.status for r in results}
            await self.db.commit()

        return QualityReport(
            catalog_id=str(catalog.id),
            score=score,
            passed=passed,
            checks=results,
            summary={
                "total_weight": total_weight,
                "awarded": awarded,
                "passed_checks": sum(1 for r in results if r.status == "pass"),
                "warned_checks": sum(1 for r in results if r.status == "warn"),
                "failed_checks": sum(1 for r in results if r.status == "fail"),
                "sku_count": len(skus),
            },
        )

    # ----- individual rules -------------------------------------------------

    async def _check_image_size(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        too_small: list[str] = []
        any_image = False
        for sku in skus:
            for img in sku.images:
                any_image = True
                if (img.width or 0) < MIN_DIMENSION or (img.height or 0) < MIN_DIMENSION:
                    too_small.append(str(img.id))
        if not any_image:
            return "fail", "No images uploaded", "Upload at least 1 image per SKU at 1024x1024 or higher."
        if too_small:
            return "fail", f"{len(too_small)} image(s) below 1024x1024", "Re-upload product images at 1024x1024 minimum."
        return "pass", "All images >= 1024x1024", None

    async def _check_white_bg(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        unprocessed = sum(1 for sku in skus for img in sku.images if not img.bg_removed)
        if unprocessed == 0 and skus:
            return "pass", "All images have a clean white background", None
        return "warn", f"{unprocessed} image(s) not yet on a white background", "Wait for the image pipeline to finish, or re-upload."

    async def _check_watermark(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        watermarked = [str(img.id) for sku in skus for img in sku.images if img.has_watermark]
        if watermarked:
            return "fail", f"{len(watermarked)} image(s) appear watermarked", "Remove any text, brand, or logo overlays — Meesho rejects watermarked images."
        return "pass", "No watermarks detected", None

    async def _check_title_length(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        problems: list[str] = []
        for sku in skus:
            title = sku.ai_title or sku.product_name or ""
            n = len(title)
            if n < TITLE_MIN or n > TITLE_MAX:
                problems.append(f"SKU {sku.product_name}: {n} chars")
        if problems:
            return "fail", f"{len(problems)} title(s) out of 30-200 chars", "Re-generate or edit titles to stay between 30 and 200 characters."
        return "pass", "All titles within length limits", None

    async def _check_title_keywords(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        thin = [
            sku.product_name
            for sku in skus
            if len((sku.ai_keywords or "").split(",")) < KEYWORD_HINT_MIN
        ]
        if thin:
            return "warn", f"{len(thin)} SKU(s) have fewer than 4 keywords", "Regenerate keywords for thin SKUs."
        return "pass", "Keyword density looks healthy", None

    async def _check_required_attributes(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        cfg = get_category_config(catalog.category or "_default")
        required = cfg.get("required", [])
        if not required:
            return "pass", "No required attributes for this category", None
        missing_per_sku: list[str] = []
        for sku in skus:
            attrs = sku.ai_attributes or {}
            missing = [k for k in required if not attrs.get(k)]
            if missing:
                missing_per_sku.append(f"{sku.product_name}: {', '.join(missing)}")
        if missing_per_sku:
            return "fail", f"{len(missing_per_sku)} SKU(s) missing required attributes", "Regenerate with category set, or edit attribute fields manually."
        return "pass", "All required attributes present", None

    async def _check_banned_words(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        hits: list[str] = []
        for sku in skus:
            haystack = " ".join(filter(None, [sku.ai_title, sku.ai_description, sku.ai_keywords])).lower()
            for word in self._banned:
                if word and word in haystack:
                    hits.append(f"{sku.product_name}: '{word}'")
                    break
        if hits:
            return "fail", f"Banned terms found in {len(hits)} SKU(s)", "Remove brand names, health claims, and prohibited keywords from titles and descriptions."
        return "pass", "No banned words detected", None

    async def _check_duplicate_check(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        # Look for catalogs (other than this one) with the same name for this user.
        same_name = (
            await self.db.execute(
                select(func.count())
                .select_from(Catalog)
                .where(
                    Catalog.user_id == catalog.user_id,
                    Catalog.id != catalog.id,
                    func.lower(Catalog.name) == catalog.name.lower(),
                    Catalog.status != "deleted",
                )
            )
        ).scalar_one()
        if same_name:
            return "warn", f"You already have {same_name} other catalog(s) with this name", "Rename to keep listings distinct."

        # Plus duplicate product_name within this catalog.
        seen: set[str] = set()
        dups: list[str] = []
        for sku in skus:
            key = (sku.product_name or "").strip().lower()
            if key in seen:
                dups.append(sku.product_name)
            seen.add(key)
        if dups:
            return "warn", f"{len(dups)} SKU(s) share product_name with another SKU", "Make each SKU's product name unique inside the catalog."
        return "pass", "No duplicates", None

    async def _check_category_mapping(self, catalog: Catalog, skus: list[SKU]) -> tuple[str, str, str | None]:
        if not catalog.category:
            return "fail", "Catalog category not set", "Pick a Meesho category for this catalog."
        if not is_valid_category(catalog.category):
            return "fail", f"'{catalog.category}' is not a known Meesho category", "Pick a category from the Meesho taxonomy."
        return "pass", f"Category '{catalog.category}' is valid", None
