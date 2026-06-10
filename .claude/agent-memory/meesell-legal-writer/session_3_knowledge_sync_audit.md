---
name: session-3-knowledge-sync-audit
description: Read-only audit of V1 legal pack 2026-06-10. Surprising findings only — marker-count reconciliation, in-product-strings folder drift after Angular 21 re-scaffold, domain inconsistency inside in-product-strings.md.
metadata:
  type: project
---

# Session 3 — Knowledge Sync Audit (2026-06-10)

Read-only. No legal files edited. Findings that are NON-obvious / contradict the tracker:

## 1. grep marker counts ≠ tracker marker counts — by design, reconciled
Raw `grep "LAWYER REVIEW"` over-counts the tracker's clause-marker numbers by +2 per customer-facing doc:
- Each doc has 1 occurrence in its **intro/preamble** sentence ("[LAWYER REVIEW] markers in this document flag...")
- Each doc has 1 occurrence in its **document-control table** ("Lawyer review markers | N — search...")
- So privacy grep=10 → 8 real markers; ToS grep=18 → 17 real markers; refund grep=3 → 2; cookie grep=2 → 1; DPA grep=7 → 6 (DPA preamble line). Tracker's stated counts (8/17/2/1/6 = 34) are the CORRECT clause-marker totals. Don't "fix" the tracker to match grep.

## 2. in-product-strings.md folder map is STALE vs Angular 21 re-scaffold — biggest finding
in-product-strings.md §1/§12 assume a flat `features/<x>/` layout that no longer exists. Actual app.routes.ts + features tree:
- §3 Profile notices → assumes `onboarding` folder; actual = `features/account/onboarding/`
- §4 Rights surfaces → assumes `dashboard → account-settings` component; **no account-settings component exists at all**. Closest surface is `features/profile/`. This is a real hand-off gap, not just a rename.
- §5 AI labels → references a `smart-picker` component scope that does not exist in the tree.
- §7 Pricing → assumes a PUBLIC `pricing/landing` page component; **only `pricing` component is the in-product per-catalog calculator at `catalogs/:id/pricing`**. No public pricing page exists yet → §7.1 tier table + §7.2 refund tile + §7.3 GST footer have nowhere to land.
- §6 images → now nested `features/images/image-uploader/`
- §8 export → now nested `features/export/export/`
- §9 footer → `landing` still exists. OK.
Conclusion: the FE hand-off keys are sound as copy, but the "where it lives" column needs a re-map pass before FE can wire. Not a publishing blocker; it IS a hand-off-accuracy blocker.

## 3. Domain inconsistency INSIDE in-product-strings.md
Line 384 uses single-e env domains `dev.mesell.xyz` / `staging.mesell.xyz` / `www.mesell.in`, while every customer-facing string in the SAME doc uses double-e `www.meesell.in`. Either the env domains are genuinely `mesell.*` (infra truth) and the public domain is `meesell.in`, or it's a typo. Flag to founder/infra — do not auto-correct without confirming the real infra domains.

## 4. "Angular 18" reference is stale
in-product-strings.md line 4 says "Angular 18 components". Codebase migrated to Angular 21 + PrimeNG 21 (commit 7001b44). Cosmetic but worth fixing on next amendment touch. Note also the doc says Material/Transloco; FE is now on PrimeNG — Transloco i18n claim should be re-verified against current FE coordinator memory before relying on the `legal.*` namespace assumption.

## 5. Blocking founder decisions unchanged since 2026-06-05
Still exactly 2 open: §15.1 entity type + §15.2 incorporator. All `[ENTITY SUFFIX]` (incl. in-product-strings + invoice + KYC) and the `[FOUNDER:...]` family collapse on incorporation. Nothing new opened.
