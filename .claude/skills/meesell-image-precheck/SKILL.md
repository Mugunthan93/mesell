---
name: meesell-image-precheck
description: >-
  MeeSell's conventions for the product-image pre-check pipeline — JPEG/format, CMYK,
  resolution, white-background, and watermark detection using Pillow + Gemini Vision. Use this
  skill WHENEVER you are creating or editing image validation/quality checks, the rembg/PIL
  image processing, or watermark/white-BG detection in the MeeSell backend — even if the user
  only says "check the uploaded image", "detect watermarks", "the white background check is
  wrong", or "validate product photos". Do NOT use it for the generic Celery worker plumbing
  (defer to meesell-services-layer) or text-prompt cost rules (defer to
  meesell-gemini-prompt-budget).
---

# MeeSell Image Pre-Check Conventions

These are the locked rules for deciding whether a seller's product photo is good enough for a
Meesho listing. They exist so cheap deterministic checks run first, the costly vision model
runs only when needed, and a borderline image never silently passes. They derive from
`CLAUDE.md` Feature 5 + Decision #4 (rembg on CPU), which win.

## The non-negotiables (and why each matters)

- **Cheap local checks first, vision model last.** Format (JPEG), CMYK color space, resolution,
  and a histogram-based white-background test are deterministic Pillow checks costing nothing —
  run them first and reject early. Only escalate to Gemini Vision (watermark / subtle quality)
  for images that pass the cheap gates. Calling the vision model on every upload, including ones
  that fail a free check, wastes the AI budget.

- **rembg on CPU, never GPU (Decision #4).** Background removal/normalisation runs on CPU at
  3–5s/image — acceptable for MVP, no GPU cost. Run it in a Celery task, not on the request.

- **Each check returns a structured verdict + reason.** A check yields `{check, passed, reason}`
  so the frontend scorecard can tell the seller exactly what to fix ("image is CMYK, convert to
  RGB"; "watermark detected top-right") — never a bare pass/fail with no guidance.

- **Fail safe, not silent.** If the vision model errors or is ambiguous, mark the check
  `needs_review` rather than auto-passing. A watermarked image slipping through is worse than a
  false flag the seller can override.

- **Validate inputs before processing.** Enforce the 10 MB cap and allowed content types at the
  boundary (the route does this); the pipeline assumes a sane file but still guards against
  corrupt/undecodable images with a clear error.

## Pipeline order

```
upload (already <=10MB, content-type checked at route)
  │
  ▼  (1) Pillow: decodes? JPEG/allowed format? resolution >= min? color space == RGB (not CMYK)?
  │      └─ any fail ──► return verdict with reason; STOP (no vision call)
  ▼  (2) Pillow histogram: white-background test (corner/edge sampling)
  │      └─ fail ──► verdict; optionally rembg can fix, else flag
  ▼  (3) Gemini Vision: watermark / logo / subtle quality  (only if 1+2 pass)
  │      └─ error/ambiguous ──► needs_review (fail safe)
  ▼  aggregate -> scorecard {overall, checks: [{check, passed, reason}]}
```

## Check verdict shape

```python
class ImageCheck(BaseModel):
    check: str          # "format" | "color_space" | "resolution" | "white_bg" | "watermark"
    passed: bool
    reason: str         # human-readable, shown on the scorecard

class ImagePrecheckResult(BaseModel):
    overall: str        # "pass" | "fail" | "needs_review"
    checks: list[ImageCheck]
```

## Pillow check examples

```python
from PIL import Image

def check_color_space(img: Image.Image) -> ImageCheck:
    if img.mode == "CMYK":
        return ImageCheck(check="color_space", passed=False,
                          reason="Image is CMYK; Meesho needs RGB. Convert before upload.")
    return ImageCheck(check="color_space", passed=True, reason="RGB")
```

Keep the cheap checks pure and unit-tested against a fixture of known-good / known-bad images,
the same way the category picker uses a golden set.

## Quick checklist before you finish an image-check task

- [ ] Deterministic Pillow checks (format, CMYK, resolution, white-BG) run BEFORE any vision call
- [ ] Gemini Vision only for images that pass the cheap gates (watermark/subtle quality)
- [ ] rembg/PIL runs on CPU in a Celery task, not on the request
- [ ] Every check returns `{check, passed, reason}` for the scorecard
- [ ] Vision error/ambiguous → `needs_review`, never auto-pass
- [ ] Corrupt/undecodable images fail with a clear reason
- [ ] Checks unit-tested against a known-good/known-bad image fixture
