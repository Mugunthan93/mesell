# Batch 6 — DRAFT findings (Home & Living + Home Utility, super_ids=12+24)

**Coverage:** 39 / 39 (100%) | Parser v0.2 | Date 2026-06-04 | Coordinator-implements fallback

## What this batch contributed

Tiny batch (39 leaves), but a meaningful Home extension to B5.

### 1. Recommended forms — median compulsory 25
Lower than B5's 33, suggesting that "Home & Kitchen" carries the long-form burden while "Home & Living" (furnishings, bedsheets) has medium-length forms.

### 2. 14 new fields, all niche
- Pet Type (4 leaves) — pet bedding
- Primary Colour / Secondary Colour (3 leaves each) — colour pairs for printed home goods
- Bolster/Cushion Cover Length/Width Size — soft furnishings sizing
- Assembly Type — for assemble-yourself furniture

→ All small-volume. Reinforces decision #6 (data-driven primitive library) — these don't need bespoke components, just the auto-classified primitives.

### 3. "Primary Colour" / "Secondary Colour" pattern
A simple Color field doesn't fit furniture/prints. Two-color products need ordered pairs. Frontend wizard renders two color-pickers labelled Primary / Secondary. Same primitive class, different field bindings.

## Cross-batch impact

| | Before B6 | After B6 |
|---|---|---|
| TRUE universals | 26 | 26 (held) |
| Cumulative leaves | 1,633 | 1,672 (44.3%) |
| Recommended fields | 0 | 0 |
| Image rule 4/1 | 100% | 100% |

→ B6 added no MVP-shifting findings. Acts as a "long tail of Home cluster" with familiar patterns. Mostly validates B5's findings rather than introducing new ones.
