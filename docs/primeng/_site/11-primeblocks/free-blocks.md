# PrimeBlocks — Free Blocks (`primeblocks.org/free`)

> **Source:** https://primeblocks.org/free — captured 2026-06-16 via headless render (Playwright), since the site is a Nuxt/PrimeVue SPA with no static/prerendered content or scrapable payload. Full-page screenshot archived at `$CLAUDE_JOB_DIR/tmp/free_page.png`.

## What this page is

The **Free Blocks** showcase — the no-purchase-required subset of PrimeBlocks. ~13 sample blocks you can copy and use without an all-access license. Each block is **Tailwind CSS markup demoed in PrimeVue** (the current PrimeBlocks product is PrimeVue-based — see `README.md`). For MeeSell (Angular + PrimeNG + Tailwind) the **layout/Tailwind structure is directly reusable**; the Prime component tags must be swapped for `@mesell/ui-kit` wrappers.

Top nav: `Blocks` · `Documentation` · `Pricing` · `Sign In` · `Get all-access`.

## The 13 free blocks (by UI category)

| # | Block | Category | Content captured | MeeSell fit |
|---|-------|----------|------------------|-------------|
| 1 | **Card** | Panel | "Card Title" + body copy | Catalog cards, generic content cards |
| 2 | **Description List** ("Movie Information") | Data display | Title/Genre/Director/Writer/Plot key-value rows | Catalog **preview/detail** — show product attributes |
| 3 | **Profile + Stats** ("Kathryn Murphy") | App / profile | Avatar + Followers 333 / Projects 26 / Collections 17 / Shots 130 | Seller profile / account header |
| 4 | **Analytics stat widget** ("Application / Analytics") | App / dashboard | 332 Active Users · 9.402 Sessions · 2.32m Avg Duration + Add / Save Changes | **Dashboard** KPI panel |
| 5 | **Sign-In (compact)** ("Welcome Back") | Auth | Sign In + Forgot Password, "Sign up" link | `/login` reference |
| 6 | **Sign-In (full form)** ("Welcome Back") | Auth | Email / Password / Remember me / Forgot password | `/login`, `/signup` reference |
| 7 | **4-Stat dashboard row** | App / dashboard | Messages 152 · Check-ins 532 · Files Synced 28.441 · Users Online 25.660 (each w/ delta) | **Dashboard** stat-card row |
| 8 | **Promo banner** ("🔥 Hot Deals!") | Marketing | Headline + copy + Learn More | Upgrade/announcement banner |
| 9 | **Community CTA** ("Join our design community" — Discord) | Marketing | Headline + Join Now | Landing / support CTA |
| 10 | **Feature grid** ("One Product, Many Solutions") | Marketing | 6 features: Built for Developers, End-to-End Encryption, Easy to Use, Fast & Global Support, Open Source, Trusted Security | **Landing** page features |
| 11 | **Image CTA** ("Create the screens…") | Marketing | Headline + Learn More / Live Demo + image | Landing hero/CTA |
| 12 | **Pricing — 3 tier** ("Pricing Plans") | Marketing | Basic $9 / Premium $29 / Enterprise $49 per month, feature bullets, Buy Now | **MeeSell pricing page** (₹499 / 999 / 1,999 plans) |
| 13 | **Pricing — toggle** ("Pricing") | Marketing | Monthly/Yearly toggle, Sketchers/Painter/Artist tiers + feature compare | **MeeSell pricing page** (monthly/yearly variant) |

## Coverage summary

- **Auth:** 2 blocks (compact + full sign-in)
- **Dashboard / app:** 3 blocks (analytics widget, 4-stat row, profile+stats)
- **Data display:** 2 blocks (card, description list)
- **Marketing:** 6 blocks (promo banner, community CTA, feature grid, image CTA, 2× pricing)

## How to use in MeeSell

These are **design/layout references**, not drop-in Angular. To adopt a block:
1. Copy the Tailwind structure (grid/flex/spacing/typography classes — portable as-is, we already use Tailwind).
2. Replace PrimeVue tags with `@mesell/ui-kit` wrappers (`mee-card`, `mee-button`, `mee-input`, etc.) and `@mesell/composites` (`stat-card`, `page-header`, `status-badge`).
3. Apply the `MeeSellPreset` tokens (brand orange, rounded radii) — already global, so blocks inherit MeeSell styling automatically.

**Highest-value blocks for V1:** the two **pricing** blocks (#12/#13) for the plans page, the **stat row** (#7) and **analytics widget** (#4) for the dashboard, and the **description list** (#2) for catalog preview.
