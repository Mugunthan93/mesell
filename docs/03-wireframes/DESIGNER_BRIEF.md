# MeeSell — Visual Designer Brief

**Status:** Ready for designer engagement
**Authored by:** meesell-frontend-coordinator, 2026-06-05
**Founder ratification:** FE-D9 (per `docs/FRONTEND_ARCHITECTURE.md §0.F`)
**Owner:** Founder picks designer & manages engagement; coordinator integrates output into `docs/FRONTEND_ARCHITECTURE.md §5A` on delivery

> Hand this file (or its contents) to your chosen designer. It contains everything they need to produce the MeeSell visual identity without reading the engineering architecture.

---

## 1. The product (60-second pitch)

**MeeSell** is a SaaS catalog tool for sellers on the Meesho marketplace (Indian e-commerce). Sellers use MeeSell to create product catalogs **10× faster** than Meesho's native upload UI, with AI-assisted category selection, autofill, image pre-check, and Meesho-format XLSX export. We replace 16 minutes of tedious form-filling per product with a guided ~1.5-minute flow.

We are **the seller's tool**, not the buyer's marketplace.

---

## 2. Target user

| Trait | Detail |
|---|---|
| Location | Tirupur (Tamil Nadu) knitwear/ethnic-wear hub primarily; pan-India broadly |
| Business size | Sub-₹1L/month revenue, 10-200 SKUs |
| Device | Low-end / mid-range Android phone (3-5 year old hardware, 2-4GB RAM) |
| Network | 2G/3G common; intermittent connectivity expected |
| Language | English V1; **Hindi + Tamil V1.5** (designer must accommodate Indic scripts) |
| Time | Catalog upload happens between manufacturing runs — fragmented, interrupted |
| Mental model | "I want to list my new design and get back to making more" |
| Trust required | They hand us their inventory list, photos, and pricing data |

---

## 3. Brand positioning

| Pillar | What it means |
|---|---|
| **Trustworthy** | Handles seller money + listings; cannot feel like a fly-by-night |
| **Fast** | Every visual decision serves the "10× faster" claim — clean, scannable, no decorative bloat |
| **Professional tool** | Feels like Photoshop or Excel — not like a shopping app |
| **Indian-context-aware** | Uses ₹ symbol, **Indian numbering** format (1,49,900 not 149,900), Hindi/Tamil-typography-respectful |
| **Mobile-first but polished** | 360px phone primary; tablet/desktop must feel intentional, not "stretched mobile" |

---

## 4. Brand anti-references (CRITICAL — what we are NOT)

| Anti-reference | Why we avoid it |
|---|---|
| **Meesho marketplace UI** (buyer side — bright pinks, deals & discounts, scrolling product grids) | We are the seller-side tool; we want the seller to feel they've stepped into a **workshop**, not a shopping aisle |
| **Generic SaaS dashboard** (Stripe-purple, Linear-grey-everywhere) | Too cold; doesn't speak to Indian seller |
| **Fintech app aesthetic** (BankBazaar, Cred) | Implies scarcity/risk; we want abundance/efficiency |
| **Indian-traditional ethnic motifs** (mandalas, saffron-flag color-coding) | Stereotyping; our users are professionals, not cultural ornaments |
| **Indie-product playfulness** (overuse of illustrations, animated mascots) | Tone-deaf for time-poor business user |

**One-line summary:** if a Tirupur seller showed our app to their accountant, the accountant should say "looks serious" — not "looks like a game" and not "looks like a Meesho ad."

---

## 5. Deliverables required

### 5.1 Color palette
- **Primary brand color** + on-primary foreground (text/icon on the primary surface)
- **Secondary color** + on-secondary
- **Neutral surface/background scale** — 5-7 stops (e.g., bg, surface, surface-variant, surface-elevated)
- **Semantic colors:** error (red family), success (green), warning (orange/amber), info (blue)
- **Outline/divider tone**
- **CRITICAL — WCAG 2.2 AA contrast on every paired combo:**
  - 4.5:1 minimum for normal text on background
  - 3:1 minimum for large text + UI components
  - Designer verifies via Stark plugin in Figma (or equivalent)
- **Light mode required for V1.** Dark mode token set nice-to-have for V1.5.

### 5.2 Typography
- **Primary typeface** (or pairing of 2 — display + body) supporting:
  - Latin script (English V1)
  - Tamil script (V1.5 — Noto Sans Tamil compatible recommended)
  - Devanagari script (V1.5 — Noto Sans Devanagari compatible)
- **Type scale** — 8 rungs covering 12-36 px range with documented line-heights
  - Example mapping: xs 12, sm 14, base 16, lg 18, xl 20, 2xl 24, 3xl 30, 4xl 36
- **Weights** — 4-5 weights (e.g., 400 regular, 500 medium, 600 semibold, 700 bold)
- Body baseline 16px minimum on mobile (legibility on low-end displays)

### 5.3 Iconography
- Pick a Material Symbols variant (outlined / filled / rounded / sharp) OR alternative icon set
- Provide ~15 key icons rendered:
  catalog · image · price · export · search · filter · add · edit · delete · check · warning · info · upload · download · settings
- All icons must be 24×24 base with `currentColor` SVG (recolorable via CSS)

### 5.4 Component visual language

Hi-fi mockups for these primitives (default + hover + active + disabled + error states where applicable):
- **Buttons** — primary, secondary, destructive, ghost variants
- **Text inputs** — Material outline OR fill style (designer recommends which); error display
- **Dropdowns** — small (≤20 entries), medium (autocomplete), large (virtual-scroll autocomplete)
- **Cards** — list-row variant (used in dashboard) + grid-tile variant
- **Empty states** — illustration approach (recommend simple line-icon over heavy illustration)
- **Loading states** — **skeleton screens recommended over spinners** for content lists
- **Snackbar/toast** — error, success, warning, info variants
- **Navigation bar** — top app shell with logo + auth state + logout

### 5.5 Key screen mockups (3 hero screens minimum)

| Screen | Why this one matters |
|---|---|
| `/` — landing page | Sets brand voice + first impression. Hero + value props + CTA. |
| `/dashboard` — populated product list | Sets the **tool feel** — table, filters, status badges. Most common return-visit screen. |
| `/catalogs/:id/edit` — wizard form with autofill overlay | The **spine feature**. Shows form layout, the yellow-highlight AI autofill UI, validation, autosave indicator. |

Each at **360px (mobile) + 1280px (desktop)** — tablet (768px) optional if budget permits.

### 5.6 Microcopy tone guide (1-2 pages)

Short doc covering:
- Headlines + button labels in seller voice (5th-grade English, action verbs, no jargon)
- Error message tone — helpful, not scolding (e.g., "Please pick from the list" not "Invalid input")
- Empty-state copy — encouraging, sets next-step context
- 5-10 example sentences translated **English → Hindi → Tamil** (V1.5 preview)

---

## 6. Technical constraints (non-negotiable for designer)

| Constraint | Detail |
|---|---|
| **Framework target** | Angular Material 3 + Tailwind CSS — designer's tokens must be exportable as CSS custom properties (`--mee-color-primary: #...`) consumable by both |
| **Spacing** | 8-point grid: 4, 8, 12, 16, 24, 32, 48, 64 px |
| **Breakpoints** | 360 (mobile baseline), 640 (sm), 768 (md), 1024 (lg), 1280 (xl) |
| **Touch targets** | ≥44×44px on every interactive element (WCAG 2.5.5) |
| **Accessibility** | WCAG 2.2 AA verified; reduced-motion + zoom-200% tolerant |
| **Output format** | Figma file (organised: tokens, components, screens) + token export (JSON or SCSS) |
| **No bitmap assets** | All icons + illustrations as SVG (scales cleanly; theme-able via `currentColor`) |

---

## 7. Reference inspirations (starting points only — not to copy)

| Reference | What to take | What to leave |
|---|---|---|
| [VariantStudio](https://variantstudio.in) — closest peer | Recognition by Indian Meesho sellers | Their visual style is dated |
| [Linear](https://linear.app) | Tool-not-app aesthetic, scannable density | Their grey is too cold for our user |
| [Notion](https://notion.so) | Text-first clarity, low chrome | Theirs is too sparse for tool feel |
| Indian SaaS examples: [Razorpay Dashboard](https://razorpay.com), [Zoho Inventory](https://zoho.com/inventory) | Indian-business-context credibility | They're too feature-dense |
| Materio / Vuexy Tailwind Admin | Material+Tailwind integration patterns | Generic, needs personality |

---

## 8. Final deliverables checklist

The designer hands back:
- [ ] **Figma file** with 3 organised pages: Tokens / Components / Screens
- [ ] **Color tokens** exported as JSON or SCSS (key+value, named semantically)
- [ ] **Typography tokens** exported as JSON or SCSS (family + scale + weights + line-heights)
- [ ] **3 hi-fi mockups** at 360 (mobile) + 1280 (desktop) for landing, dashboard, catalog-form
- [ ] **Component visual language sheet** — all primitives at all states
- [ ] **Microcopy tone guide** (1-2 pages)
- [ ] **Accessibility verification** — Stark plugin screenshot or equivalent contrast report
- [ ] **15 SVG icons** with the icon-set name documented

---

## 9. What is NOT in scope for this engagement

- Wireframes for all 10 routes (we extrapolate from the 3 hero mockups using the component language)
- Logo design (separate engagement; placeholder type-set logo is fine for V1)
- Marketing site beyond the landing route
- iOS/Android app icons (V1.5 PWA installable)
- Print/billboard adaptations
- Animation choreography beyond the motion-token specification

---

## 10. Engagement formats (founder picks one)

| Format | Typical cost (₹) | Timeline | Notes |
|---|---|---|---|
| **99designs design contest** | 15k - 40k | 3-4 weeks | Multiple concepts, pick winner |
| **Behance / Dribbble** sourced freelancer | 30k - 80k | 4-6 weeks | Single-track engagement |
| **Toptal / Upwork** vetted designer | 40k - 120k | 4-6 weeks | Higher quality bar |
| **Local Bangalore/Mumbai designer** | 40k - 100k | 4-6 weeks | In-person briefing possible |
| **AI-assisted self-serve** (Galileo, v0, Figma AI) | 0 - 5k tooling | 1-2 weeks | Working-draft only; revisit post-V1 |

For MeeSell V1 timeline pressure: founder may want the **AI-assisted self-serve** path to unblock V1 ship, then engage a real designer post-launch for V1.5 brand refinement.

---

## 11. Timeline expectations

| Week | Milestone |
|---|---|
| 1 | Brief signed off + designer selected |
| 2-3 | Concept exploration (2-3 directions) |
| 4 | Chosen direction refined |
| 5-6 | Full deliverables produced |
| 7 | Feedback rounds + final delivery |

---

## 12. Integration protocol (coordinator side)

Once designer's deliverables land:

1. Founder reviews + ratifies tokens
2. `meesell-frontend-coordinator` updates `docs/FRONTEND_ARCHITECTURE.md §5A` values from designer artefacts (replacing the FE-D9 placeholders)
3. §5A status flips from PARTIAL LOCK → FULL LOCK
4. Coordinator dispatches `meesell-angular-ui-styler` with the ratified tokens + Figma file references
5. ui-styler produces SCSS token files, theme, Tailwind bridge per §5A
6. Component-builder (if not already dispatched in parallel) consumes the styled primitives

---

## 13. Coordinator contact for designer questions

The designer may have technical questions during the engagement. Founder routes those to `meesell-frontend-coordinator` via:
- Updating `docs/03-wireframes/` with a `QUESTIONS.md` file
- Coordinator responds via the same file on next session
- High-velocity questions: founder relays directly

---

**End of brief.** Designer has everything needed to produce.
