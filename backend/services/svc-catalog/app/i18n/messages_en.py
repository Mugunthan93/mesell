"""i18n English message registry — V1 validation_message_id → English string map.

Source: ``BACKEND_ARCHITECTURE.md`` §5A.I locks the registry's name
(``VALIDATION_MESSAGES``), its type (``dict[str, str]``), and the constraint
that every key conforms to §5A.H:

    {domain}.{field_or_subdomain}.{constraint}

i.e. three snake_case segments, regex
``^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$``.

§19 CI Contract 10 scans this registry against the regex; CI fails on the
first non-conforming key. The registry is plural-localised forward-compat:
V1 ships ``messages_en.py`` only; V1.5 adds ``messages_ta.py`` /
``messages_hi.py`` (§3.H locks the placeholder; do NOT create the V1.5 files
in V1 per §5A.J).

§5A.I English-string CONTENT is NOT locked — strings grow incrementally as
each module is constructed. This V1 inventory ships the canonical ~50 IDs
referenced by §7 (iam, 8) + §4.B (auth dep, 3) + §8 (customer, 6) + §9
(category, 4) + §10 (catalog, 5) + §11 (image, 5) + §12 (pricing, 5) +
§13 (dashboard, 1) + §14 (export, 7) + §4 (core, 4) plus the
``validation.body.*`` and ``validation.fields.*`` legals used by FastAPI
body-validation error responses (§4.F handler).

Wording principles (services-builder finalised):

1. Speak to the seller in second person ("Your", "You").
2. State the problem THEN the recovery action in one sentence each.
3. Never expose internal IDs, traceback fragments, or vendor names that
   the seller cannot act on. Vendor outages get the public-facing label
   (e.g. "OTP service" not "MSG91").
4. For legally sensitive copy (DPDP consent, retention) consult
   ``meesell-legal-writer`` memory before finalising. The strings below
   stay neutral and instructional — no DPDP/retention wording lives here.
"""

from __future__ import annotations

# ----------------------------------------------------------------------------
# VALIDATION_MESSAGES registry
# Keys MUST conform to §5A.H. Test in ``test_messages_en_id_regex.py``.
# ----------------------------------------------------------------------------
VALIDATION_MESSAGES: dict[str, str] = {
    # ── core/auth.py (§4.B + §7.G — auth-dependency surface) ──────────────
    "auth.token.missing": "You're not signed in. Please sign in to continue.",
    "auth.token.expired": "Your session has expired. Please sign in again.",
    "auth.user.not_found": "We couldn't find your account. Please sign in again.",
    # ── §7 iam (8 module-specific IDs) ───────────────────────────────────
    "validation.phone.invalid_format": (
        "Please enter a valid 10-digit Indian mobile number."
    ),
    "validation.otp.invalid_format": (
        "Please enter the 6-digit OTP we sent to your phone."
    ),
    "validation.webhook.malformed_payload": (
        "We received an unreadable webhook payload."
    ),
    "auth.otp.invalid": (
        "That OTP didn't match. Please check the code and try again."
    ),
    "auth.otp.attempts_exceeded": (
        "Too many wrong attempts. Please request a new OTP after a few minutes."
    ),
    "auth.msg91.unavailable": (
        "Our OTP service is temporarily unavailable. Please try again in a moment."
    ),
    "auth.refresh.invalid": (
        "Your session can't be refreshed. Please sign in again."
    ),
    "auth.webhook.signature_invalid": (
        "Webhook signature could not be verified."
    ),
    # ── §8 customer (6 module-specific IDs) ──────────────────────────────
    "validation.pincode.invalid_format": (
        "Please enter a valid 6-digit pincode."
    ),
    "validation.super_category.unknown": (
        "We don't recognise that category group. Please pick from the list."
    ),
    "customer.profile.not_found": (
        "We couldn't find your seller profile. Please complete onboarding."
    ),
    "customer.super_category.not_declared": (
        "Please select your seller category group before listing this product."
    ),
    "customer.compliance.missing_fields": (
        "Some compliance details are missing from your profile. Please complete them to continue."
    ),
    "customer.profile.incomplete_for_category": (
        "Your seller profile is incomplete for this category. Please update your profile to list here."
    ),
    # ── §9 category (4 module-specific IDs) ──────────────────────────────
    "category.lookup.not_found": (
        "We couldn't find that category. Please pick another from the list."
    ),
    "category.field_enum.not_found": (
        "We couldn't load the options for this field. Please refresh the page."
    ),
    "validation.suggest_q.too_short_or_long": (
        "Please type between 2 and 60 characters to search categories."
    ),
    "validation.browse.invalid_pagination": (
        "Page or limit is out of range. Please try a smaller page size."
    ),
    # ── §10 catalog (5 module-specific IDs + dynamic per-field) ──────────
    "catalog.product.not_found": (
        "We couldn't find that product. It may have been deleted."
    ),
    "catalog.catalog.not_found": (
        "We couldn't find that catalog. It may have been deleted."
    ),
    "catalog.draft.missing": (
        "No saved draft was found for this product."
    ),
    "catalog.autofill.internal_error": (
        "Auto-fill ran into a problem. Please try again or fill the fields manually."
    ),
    "catalog.profile.incomplete_for_category": (
        "Please complete your seller profile for this category before creating a product."
    ),
    # ── §10 catalog — dynamic per-field validation IDs (samples) ─────────
    # Per §5A.J the registry grows incrementally; the per-field IDs land as
    # they are referenced. These 5 are documented in §10 and §5A.I.
    "validation.fields.unknown_key": (
        "One of the fields you sent is not part of this product's category. Please remove it."
    ),
    "validation.body.malformed_json": (
        "The data we received couldn't be read. Please try again."
    ),
    "validation.completeness.missing_compulsory": (
        "Some required fields are still empty. Please fill them before marking the product ready."
    ),
    "validation.product_name.too_short": (
        "Product name must be at least 3 characters."
    ),
    "validation.product_name.too_long": (
        "Product name is too long. Please shorten it."
    ),
    "validation.product_name.no_special_chars": (
        "Product name may not contain special characters except hyphens."
    ),
    "validation.description.too_short_or_long": (
        "Description length is out of range. Please adjust it."
    ),
    # ── §11 image (5 module-specific IDs) ────────────────────────────────
    # Wording updated at §11 construction time per §11.B.1 (JPEG only, 4 slots).
    "validation.image.invalid_format": (
        "Only JPEG images are accepted. Please upload a JPEG file."
    ),
    "validation.image.too_large": (
        "This image is too large. Please upload a file under 10 MB."
    ),
    "validation.image.invalid_idx": (
        "Please choose an image slot between 1 and 4."
    ),
    "image.slot.occupied": (
        "This image slot already has an image. Please remove it first or pick another slot."
    ),
    "image.not.found": (
        "We couldn't find that image. It may have been deleted."
    ),
    # ── §12 pricing (5 module-specific IDs) ──────────────────────────────
    "validation.price.invalid_input": (
        "Please enter a valid price greater than zero."
    ),
    "pricing.commission.missing": (
        "We couldn't load the commission rate for this category. Please try again later."
    ),
    "pricing.alert.low_margin": (
        "Your profit margin is below the safe threshold. Consider raising your selling price."
    ),
    "pricing.alert.high_mrp_multiplier": (
        "Your MRP is much higher than your cost. Verify this is the price you want to advertise."
    ),
    "pricing.alert.thin_profit": (
        "Your profit per unit is low. Consider revising your cost or selling price."
    ),
    # ── §13 dashboard (1 module-specific ID) ─────────────────────────────
    "validation.dashboard.invalid_pagination": (
        "Page or limit is out of range. Please try a smaller page size."
    ),
    # ── §14 export (7 module-specific IDs) ───────────────────────────────
    "export.not.found": (
        "Export not found."
    ),
    "export.product.not_ready": (
        "Product is not ready for export. Complete the product setup first."
    ),
    "export.front_image.missing": (
        "A front image is required to export with images. Upload an image in slot 1."
    ),
    "export.enum.validation_failed": (
        "Export failed: an invalid value was detected. Please re-run the export."
    ),
    "export.compliance.strategy_failed": (
        "Export failed: unable to process compliance information."
    ),
    "export.xlsx.build_failed": (
        "Export failed: unable to generate the XLSX file."
    ),
    "export.round_trip.mismatch": (
        "Export failed: data validation mismatch. Please re-run the export."
    ),
    # ── §4.C tenancy (1 cross-cutting ID) ────────────────────────────────
    "tenancy.cross_user.access": (
        "You do not have access to this resource."
    ),
    # ── §4.E plan_guard (1 cross-cutting ID) ─────────────────────────────
    "plan.limit.exceeded": (
        "You've reached your plan's limit. Upgrade to continue."
    ),
    # ── §4.F server fallback (1 cross-cutting ID) ────────────────────────
    "server.internal.error": (
        "Something went wrong on our end. Please try again."
    ),
    # ── §6A ai_ops (1 cross-cutting ID — budget hard-stop fallback) ──────
    "ai_ops.budget.exhausted": (
        "AI assistance is taking a break for the day. Please fill in manually "
        "or try again tomorrow."
    ),
}


__all__ = ["VALIDATION_MESSAGES"]
