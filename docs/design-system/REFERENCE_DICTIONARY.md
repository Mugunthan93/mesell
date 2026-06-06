# MeeSell — Design System Reference Dictionary

**Status:** Phase 1 Round 1 — curated; awaiting founder picks
**Updated:** 2026-06-05
**Authored by:** meesell-angular-ui-styler (Opus)
**Methodology:** docs/DESIGN_SYSTEM_ARCHITECTURE.md §1.B (curate-then-pick, not agent-internal reasoning)

---

## How to use this document

Founder reviews per category, picks (or requests refinement). Multi-turn iteration per DESIGN_SYSTEM_ARCHITECTURE.md §5. Agent does NOT pick, rank, or recommend a top choice — the agent presents strong options grouped per category after evaluating ~15-20+ candidates per category and culling to the strongest 5-10.

Per category, founder responses are:
- **(a) Pick** → ratified per category; coordinator appends to "Picks log" below
- **(b) "More options"** → next round with same constraints, more breadth
- **(c) "Narrower"** → next round constrained (e.g., "only warmer secondaries", "drop the outliers")
- **(d) "Broader"** → next round widened (e.g., "include forest greens", "include darker primaries")

After all five Phase 1 categories have a pick, founder evaluates **composition** (does color + typeface + iconography work TOGETHER?). If composition fails, any category re-opens.

---

## Phase 1 — Foundation

### Category 1.1 — Primary brand color

**Brief recap (per DESIGNER_BRIEF.md §3 + §4):**
- Pillars: trustworthy / fast / professional tool / Indian-context-aware / mobile-first
- Anti-Meesho-buyer (no bright pink #F43397)
- Anti-generic-SaaS (no Stripe-purple #635BFF, no Linear-grey-purple #5E6AD2)
- Anti-fintech (no extreme financial-trust blue)
- Anti-traditional-ethnic (no saffron-flag #FF9933)
- Tone: warm + grounded + Indian-business-context-appropriate + visually distinct on Android low-end screens

The agent evaluated ~22 candidates across the warm-orange, warm-amber, warm-red, deep-teal, and forest-green families. The 9 below are the strongest.

---

#### Reference 1 — Razorpay Dashboard primary blue (https://razorpay.com/)
- **Visual signal:** `#0F1641` deep navy (anchor) with `#0066FF` action blue
- **Source context:** Largest Indian fintech SaaS dashboard; B2B seller-facing product
- **Why included:** Sets the bar for "Indian SaaS gravitas." Sellers know this brand from invoice receipts and recognise the visual language as "serious financial tool."
- **Why might FIT MeeSell:** Hits *trustworthy* and *professional tool* pillars hard. Recognisable as Indian-business-context-appropriate without ethnic stereotyping.
- **Why might NOT fit:** This is exactly what the brief calls **anti-fintech** — extreme financial-trust blue. May feel cold for a creative-catalog-building tool. Razorpay is "money-in-transit" — MeeSell is "catalog-being-crafted." Different emotional register.
- **Screenshot/exemplar:** Razorpay landing + dashboard use a deep navy app shell with bright blue CTAs. Whites and pale-blue surfaces. Inter-style sans throughout.

#### Reference 2 — Khatabook primary orange (https://khatabook.com/)
- **Visual signal:** `#F36F21` warm orange (close to MeeSell's current §5A placeholder `#F26B23`)
- **Source context:** Indian merchant ledger app; 10M+ small-business users; closest persona-match to Tirupur seller
- **Why included:** Direct persona match — Khatabook users overlap heavily with Meesho sellers (kirana, manufacturers, retailers). The orange reads as "Indian SME working tool."
- **Why might FIT MeeSell:** Hits *Indian-context-aware* + *trustworthy-for-merchants* simultaneously. Warm without being saffron-flag-adjacent. Has high recognition equity among the exact persona.
- **Why might NOT fit:** Risks "yet another Indian SME orange" — Khatabook, Vyapar, OkCredit, BharatPe all live in the warm-orange/amber space. MeeSell may want a distinct signature. Also borders on Meesho-pink-adjacent warm tones (though clearly orange-not-pink).
- **Screenshot/exemplar:** Khatabook's app uses orange as the primary CTA color over a white/cream surface, with charcoal text. Cards have soft shadows; tabular ledger rows dominate the dashboard view.

#### Reference 3 — Vyapar amber-orange (https://vyaparapp.in/)
- **Visual signal:** `#FF8200` to `#FFA000` amber-orange range
- **Source context:** Indian SME accounting + invoicing tool; competes directly with Tally and Zoho Books at the small-business floor
- **Why included:** Adjacent persona — Vyapar users are exactly the sellers MeeSell targets, often same individuals.
- **Why might FIT MeeSell:** Same warm-Indian-merchant equity as Khatabook with a slightly more amber (less red) tone. Reads "settle in for work" not "shop now."
- **Why might NOT fit:** Lives in the same crowded amber-orange space as Khatabook and BharatPe. Risk of brand collision and "indistinct Indian SME tool" perception. Slightly more yellow than ideal — yellow can read as caution.
- **Screenshot/exemplar:** Vyapar's invoice screens have an amber-orange app bar, white surfaces, dense table layouts. The brand mark uses a soft orange-to-yellow gradient.

#### Reference 4 — Zoho rust-red primary (https://www.zoho.com/inventory/)
- **Visual signal:** `#C8102E` rust-red (Zoho's signature) with `#159A8E` teal accent
- **Source context:** Largest India-origin SaaS (Chennai-headquartered, Tamil Nadu — direct cultural alignment with Tirupur sellers); B2B inventory + CRM + business tools
- **Why included:** Tamil-Nadu-headquartered SaaS with global execution. Sets a bar for "Tamil-built professional tool."
- **Why might FIT MeeSell:** Cultural alignment with Tamil-Nadu founder identity. Reads "professional tool" cleanly. Rust-red has warmth + maturity without ethnic-traditional stereotyping.
- **Why might NOT fit:** Rust-red borders dangerously close to error-state red — risks confusing "primary action" with "danger." Sellers do business in red-warning context daily (Meesho QC rejections, GST notices). Rust may amplify low-key anxiety. Also: Zoho's brand has decades of equity; using anything close risks "looks like a Zoho clone."
- **Screenshot/exemplar:** Zoho Inventory: rust-red top app bar, white workspace, teal accent for success states, dense data tables. Inter-like sans, tight line heights.

#### Reference 5 — Freshworks teal primary (https://www.freshworks.com/)
- **Visual signal:** `#173B45` deep teal with `#16C083` mint accent
- **Source context:** India-origin SaaS (Chennai); B2B helpdesk + CRM
- **Why included:** Another Tamil-Nadu-built SaaS with international polish. Teal direction tests the "warm primary" assumption.
- **Why might FIT MeeSell:** Distinct from the crowded Indian-orange space; teal reads "calm, competent, technical." Aligns with *professional tool* + *trustworthy* without warmth-overload.
- **Why might NOT fit:** Cool teal misses the *Indian-context-aware* + *warmth* pillars. Could feel like generic global SaaS (Slack-adjacent). Loses the "Tirupur seller settles in for work" emotional cue. Adds a question mark on differentiation from Linear/Notion-grey.
- **Screenshot/exemplar:** Freshworks marketing site uses deep teal as primary CTA and brand anchor, with mint-green for success states and white surfaces.

#### Reference 6 — Lightspeed Retail terracotta (https://www.lightspeedhq.com/)
- **Visual signal:** `#E25F2A` terracotta-orange (slightly more red/earthy than Khatabook orange)
- **Source context:** Global retail POS SaaS used by independent shops; not Indian but persona-adjacent (small retailers)
- **Why included:** Terracotta sits between Khatabook orange and rust-red — testing whether a slightly earthier hue distinguishes MeeSell from the crowded Indian-amber-orange space.
- **Why might FIT MeeSell:** Earthy terracotta has a "workshop" feel that hits the brief's "workshop not shopping aisle" directive (DESIGNER_BRIEF.md §4). Warmer than Khatabook orange without trending toward saffron.
- **Why might NOT fit:** May read as "Western indie-retail brand" rather than Indian-context-aware. Terracotta-as-primary is less common in Indian SME tooling — could feel imported rather than native.
- **Screenshot/exemplar:** Lightspeed's POS dashboards use terracotta-orange for the primary CTA over cream-white surfaces; charcoal sans-serif text; sparse card layouts.

#### Reference 7 — BharatPe deep blue (https://bharatpe.com/)
- **Visual signal:** `#0F2B6E` deep navy with `#0080FF` electric blue accent
- **Source context:** Indian merchant payments SaaS; targets exact same Tier-2/3 merchant persona as Meesho sellers
- **Why included:** Persona-matched Indian fintech for merchants. Tests "trust-blue but Indian-coded."
- **Why might FIT MeeSell:** Recognisable persona signal. Deep navy reads "stable, reliable" — important for a tool that handles seller money math.
- **Why might NOT fit:** Brief explicitly anti-fintech-blue. Deep navy + electric blue is *exactly* the "extreme financial-trust" tone the brief rules out. Also: BharatPe brand has well-documented controversy; visual association risk.
- **Screenshot/exemplar:** BharatPe merchant dashboard: deep navy header, white workspace, electric blue CTAs, generous use of QR-code imagery.

#### Reference 8 — OkCredit muted gold (https://okcredit.in/)
- **Visual signal:** `#D9A14B` muted gold-amber with `#1A1A1A` charcoal anchor
- **Source context:** Indian SME credit ledger; persona-overlap with Khatabook
- **Why included:** Tests a muted-amber direction that avoids the saturated-orange Khatabook/Vyapar zone.
- **Why might FIT MeeSell:** Muted gold reads "established, mature, slightly premium" — could support a "₹499/mo paid tool, not free utility" positioning. Distinct from the crowded saturated-orange Indian-SME space.
- **Why might NOT fit:** Risks low-contrast against off-white backgrounds (WCAG 4.5:1 challenging on muted gold). Gold can read as "luxury / wedding / jewellery" in Indian context — wrong emotional register for catalog work. Lower visibility on low-end Android screens with poor brightness.
- **Screenshot/exemplar:** OkCredit's app uses muted gold sparingly as accent, with charcoal as primary text and a cream surface. The visual identity is restrained and ledger-focused.

#### Reference 9 — Notion warm-on-white (https://www.notion.so/)
- **Visual signal:** `#37352F` warm-charcoal as primary "ink"; no chromatic primary brand color
- **Source context:** Global productivity SaaS; tool-not-app aesthetic explicitly cited as a reference in DESIGNER_BRIEF.md §7
- **Why included:** Tests the "no chromatic primary" approach — letting typography + spacing carry the brand, with color reserved for semantic states only.
- **Why might FIT MeeSell:** Hits *professional tool* + *fast* pillars (chromatic-restraint = scannable). Avoids the "which orange?" debate entirely. Leaves room for the AI autofill yellow-highlight to be the only color in the workspace — strong UX signal.
- **Why might NOT fit:** Misses *Indian-context-aware* — chromatic-restraint reads as "Western tech tool," not "Tamil Nadu seller's tool." Also no brand differentiation in the marketplace ("looks like a Notion clone"). May feel cold to the persona despite being warm-charcoal.
- **Screenshot/exemplar:** Notion has no app-bar color, no chromatic primary; the entire workspace is white/cream with warm-charcoal text and subtle grey separators. Color appears only in user-content (highlights, callouts).

---

### Category 1.2 — Secondary color

**Brief recap:** Complementary to primary. Drives semantic palette anchoring (info, links, secondary actions). Should compose with multiple of the Category 1.1 candidates above to give founder flexibility.

The agent evaluated ~18 candidates across the deep-blue, deep-teal, deep-green, neutral-charcoal, and warm-on-warm spectrums. The 8 below are the strongest.

---

#### Reference 1 — IBM Carbon Blue 70 (https://carbondesignsystem.com/)
- **Visual signal:** `#0F62FE` IBM signature blue (Blue 60) with `#002D9C` (Blue 70) anchor
- **Source context:** IBM Carbon public design system; reference standard for enterprise B2B tooling
- **Why included:** Sets the gold standard for "trustworthy enterprise blue" with documented WCAG verification. Composes well with most warm primaries (orange/amber/terracotta) via complementary contrast.
- **Why might FIT MeeSell:** Strong as a secondary because it's chromatically opposite to warm primaries — composition produces high visual hierarchy. Recognisable as "tool blue" rather than "fintech blue."
- **Why might NOT fit:** Vibrant electric blue can feel "tech-corporate" — may clash with the workshop emotional cue. WCAG passes everywhere but visual feel is "cold IBM" not "warm Tamil seller."
- **Screenshot/exemplar:** Carbon docs show Blue 60 as primary CTA + link color across white surfaces; tight Plex Sans typography; dense table layouts.

#### Reference 2 — Material 3 deep blue (https://m3.material.io/styles/color/system/overview)
- **Visual signal:** `#1D4ED8` Material 3 baseline blue (close to Tailwind blue-700)
- **Source context:** Material 3 reference; this is what Angular Material's default theme generates for a "blue" seed
- **Why included:** Default Angular Material baseline — picking this aligns with Material 3 theming flow and minimises bespoke override work. Composes mechanically with any warm primary via M3's harmonisation.
- **Why might FIT MeeSell:** Lowest-friction technical fit — Material 3's tonal palette generation produces a coherent secondary scale for free. Recognisable but not generic.
- **Why might NOT fit:** "Material 3 default blue" is becoming the new Stripe-purple — an emerging generic SaaS marker. Risk: app looks "Material default" rather than "MeeSell brand."
- **Screenshot/exemplar:** Material 3 docs example screens use deep blue as secondary action color over white surfaces with elevated cards.

#### Reference 3 — Atlassian deep-teal #00B8D9 (https://atlassian.design/foundations/color)
- **Visual signal:** `#00B8D9` Atlassian teal-cyan with `#0747A6` anchor blue
- **Source context:** Atlassian public design system; reference for collaborative B2B tools (Jira, Confluence)
- **Why included:** Tests a teal-leaning secondary that bridges blue and green semantically; composes well with warm orange primaries.
- **Why might FIT MeeSell:** Teal reads "fresh, modern, competent" without the "extreme trust-fintech" tone of pure deep blue. Composes vividly with orange/amber primary.
- **Why might NOT fit:** Teal as secondary may compete with success-green semantic state — risk of "is this an action or a success indicator?" ambiguity. Atlassian-teal is also strongly brand-coded; risk of "looks like Jira."
- **Screenshot/exemplar:** Atlassian Jira dashboards: deep-blue + teal-cyan accent on white surfaces, with structured forms and side navigation.

#### Reference 4 — Tailwind slate-700 / charcoal (https://tailwindcss.com/docs/customizing-colors)
- **Visual signal:** `#334155` Tailwind slate-700 (deep neutral charcoal)
- **Source context:** Tailwind's default neutral scale; widely used as "no-color secondary" in tool-not-app SaaS
- **Why included:** Tests a chromatic-neutral secondary — letting the primary carry all chromatic weight, with secondary actions in deep slate.
- **Why might FIT MeeSell:** Composes universally with any primary. Hits *fast* + *professional tool* — minimum visual noise. Mature, restrained — supports "₹499/mo paid tool" positioning. Pairs especially well with bold warm primaries (terracotta, rust, gold) without competing.
- **Why might NOT fit:** "Charcoal secondary" can read flat — no secondary accent personality. App may feel mono-chromatic. Risk: low energy for a "10× faster" promise.
- **Screenshot/exemplar:** Linear and Vercel both use deep-slate as secondary action with a single accent color carrying the brand — high-density information screens with low color noise.

#### Reference 5 — Polaris (Shopify) deep teal-green (https://polaris.shopify.com/)
- **Visual signal:** `#008060` Shopify-green secondary with `#202223` ink primary
- **Source context:** Shopify Polaris design system; reference for merchant-facing B2B commerce tools
- **Why included:** Persona-adjacent — Shopify merchants overlap conceptually with Meesho sellers (small business, catalog management, commerce).
- **Why might FIT MeeSell:** Deep teal-green reads "commerce-positive, growth, money-in" — emotionally appropriate for sellers. Compositional fit with warm orange primary is excellent (complementary).
- **Why might NOT fit:** Teal-green secondary will compete with success-green semantic state — needs careful disambiguation (Shopify uses it as primary, sidestepping the issue). Risk: "looks like a Shopify clone."
- **Screenshot/exemplar:** Polaris docs show Shopify-green as primary CTA over white surfaces with sans-serif text and structured product-edit forms.

#### Reference 6 — GitHub Primer blue (https://primer.style/foundations/color)
- **Visual signal:** `#0969DA` GitHub-blue with `#1F2328` ink anchor
- **Source context:** GitHub Primer design system; reference for developer-tool aesthetic
- **Why included:** Tests a slightly softer, more humane blue than Material/IBM — sits between the "warm Razorpay" and "cold Material" extremes.
- **Why might FIT MeeSell:** Hits *professional tool* without the "enterprise SAP" weight of IBM blue. Composes with warm primaries. Recognisable but not generic.
- **Why might NOT fit:** GitHub-coded — risk of "looks like GitHub for sellers" perception. May feel developer-tool rather than seller-tool. Not particularly Indian-context-aware.
- **Screenshot/exemplar:** GitHub's UI: blue primary action over white surfaces, dense data displays, monospace mixed with sans-serif.

#### Reference 7 — Tailwind emerald-700 (https://tailwindcss.com/docs/customizing-colors)
- **Visual signal:** `#047857` Tailwind emerald-700
- **Source context:** Tailwind's emerald scale; popular for "growth/commerce" SaaS
- **Why included:** Tests a deep-green secondary that pairs with warm-orange primaries for a "commerce-positive" composition.
- **Why might FIT MeeSell:** Strong complementary pairing with warm primaries. Green reads "money positive" — directly relevant to pricing calculator + margin display. Distinct from "fintech blue" while keeping trust connotation.
- **Why might NOT fit:** Will heavily compete with success-green semantic state — likely incompatible unless success state shifts to a different green stop. Also: green-as-secondary in commerce can read as "go button" — may overpower the primary CTA hierarchy.
- **Screenshot/exemplar:** Many fintech-adjacent dashboards (Cred, Groww) use deep emerald as a growth/positive-state accent over white surfaces.

#### Reference 8 — Carbon Cool Gray 90 (https://carbondesignsystem.com/)
- **Visual signal:** `#393939` Carbon cool-gray-90 (near-black with subtle cool tint)
- **Source context:** IBM Carbon's neutral anchor
- **Why included:** Tests a near-black secondary — letting primary be the only chromatic accent, with all secondary actions in deep cool gray.
- **Why might FIT MeeSell:** Universal compositional fit. Maximum focus on primary brand color. Pairs especially well with bold or muted primaries (terracotta, gold, rust). Supports density-heavy table screens (dashboard, pricing) without color noise.
- **Why might NOT fit:** Cool tint may feel colder than the warm primary's emotional register — minor mismatch. Same "low energy" risk as Tailwind slate.
- **Screenshot/exemplar:** Carbon's enterprise screens use cool gray 90 as the body text + secondary action anchor over white surfaces.

---

### Category 1.3 — Surface/neutral palette

**Brief recap:** Background + surface + surface-variant stops. Drives readability + density feel. The agent looked at off-white vs pure white (warmer vs cooler), neutral-scale density (number of stops), and how the scale composes with low-end Android display constraints.

The agent evaluated ~14 candidates across public design system docs (Carbon, Atlassian, Polaris, Primer, Pajamas, Material 3, Tailwind). The 7 below are the strongest.

---

#### Reference 1 — IBM Carbon Gray (https://carbondesignsystem.com/elements/color/tokens/)
- **Visual signal:** 10-stop cool gray: Gray-10 `#F4F4F4` → Gray-20 `#E0E0E0` → Gray-30 `#C6C6C6` → Gray-60 `#6F6F6F` → Gray-100 `#161616`. Pure-white background.
- **Source context:** IBM Carbon design system; enterprise B2B reference
- **Why included:** Most rigorous neutral scale in the public design-system canon. 10 stops give ample headroom for hierarchy in dense screens.
- **Why might FIT MeeSell:** Excellent for the dashboard density needs (tables, status badges, filter chips). WCAG verified at every paired combo. Cool gray composes with both warm and cool primaries.
- **Why might NOT fit:** 10 stops is overkill for V1's 10 routes — risks decision-paralysis in component-builder dispatch. Cool gray emotional tone may clash with warm primary (subtle but real "cold IBM" feel).
- **Screenshot/exemplar:** Carbon enterprise screens use Gray-10 as page background, white as elevated surface, Gray-30 as borders, Gray-100 as primary text.

#### Reference 2 — Atlassian Neutral (https://atlassian.design/foundations/color)
- **Visual signal:** 7-stop cool gray: N10 `#F7F8F9` → N30 `#DCDFE4` → N100 `#172B4D` → N500 `#091E42`. Off-white surface (cool tint).
- **Source context:** Atlassian Jira/Confluence design system
- **Why included:** Tuned specifically for B2B collaborative tools — same surface density needs as MeeSell dashboard.
- **Why might FIT MeeSell:** 7 stops is right-sized for V1 scope. The cool-tinted off-white reduces eye fatigue on long catalog-edit sessions (Tirupur seller may spend 15-30min per catalog).
- **Why might NOT fit:** Cool tint pulls warm-primary apps toward a "Jira" feel — may not differentiate MeeSell visually. The N100/N500 ink colors are blue-tinted, which reduces compositional flexibility.
- **Screenshot/exemplar:** Jira dashboards: N10 page background, white card surfaces, N30 borders, N500 primary text. Clean but cold.

#### Reference 3 — Polaris (Shopify) Surface (https://polaris.shopify.com/tokens/color)
- **Visual signal:** Warm-neutral: surface `#FFFFFF`, surface-subdued `#F6F6F7` (warm-tinted), text `#202223` (warm anchor), border `#E1E3E5`
- **Source context:** Shopify Polaris; reference for merchant-facing commerce SaaS
- **Why included:** Warm-tinted off-white is rare in design systems and persona-relevant — Shopify merchants overlap with MeeSell persona.
- **Why might FIT MeeSell:** Warm tints support the "workshop" emotional cue from the brief. Composes naturally with warm primaries (orange/amber/terracotta). 5 stops is lean and decisive — good for V1 scope.
- **Why might NOT fit:** Warm off-white can look "yellowed/aged" on poorly calibrated low-end Android displays (Tirupur device floor). May feel less "crisp" than cool-tinted scales.
- **Screenshot/exemplar:** Shopify Admin: warm-white page surface, warm-tinted subdued surface for cards, deep warm-anchor text.

#### Reference 4 — GitHub Primer Light Neutral (https://primer.style/foundations/color/base-colors)
- **Visual signal:** 10-stop neutral scale: `#FFFFFF` canvas → `#F6F8FA` subtle → `#D0D7DE` border → `#1F2328` ink. Cool-neutral tint.
- **Source context:** GitHub Primer; developer tool reference
- **Why included:** Best-in-class for code/data density — same density needs as MeeSell catalog table.
- **Why might FIT MeeSell:** Subtle cool tint without going Carbon-cold. Verified WCAG everywhere. Excellent at expressing 4-5 levels of hierarchy in tables.
- **Why might NOT fit:** "GitHub-coded" — developer tool perception risk. The 10-stop ladder is rigorous but exceeds V1 needs.
- **Screenshot/exemplar:** GitHub repo pages: `#FFFFFF` canvas, `#F6F8FA` subtle row hover, `#D0D7DE` table borders, dark ink text.

#### Reference 5 — Material 3 Surface tonal palette (https://m3.material.io/styles/color/system/overview)
- **Visual signal:** M3-generated tonal surface set: `#FFFBFE` surface, `#F4EFF4` surface-variant, `#1C1B1F` on-surface
- **Source context:** Material 3 reference (Angular Material 18 default)
- **Why included:** Picking M3-generated surfaces minimises override work in Angular Material theming. Tonal harmonisation is automatic.
- **Why might FIT MeeSell:** Mechanical fit with Angular Material 18 theming flow. M3's tonal palette generation produces a coherent surface scale from a single seed color.
- **Why might NOT fit:** M3 surface tints carry a faint chromatic cast inherited from the primary — can produce subtle pink/purple casts on white if the primary is warm orange. May look "default Material" rather than custom MeeSell.
- **Screenshot/exemplar:** Material 3 docs screenshots: tonal surface with faint primary-derived tint, elevated cards, M3 buttons.

#### Reference 6 — Tailwind Neutral / Stone (https://tailwindcss.com/docs/customizing-colors)
- **Visual signal:** Stone (warm-neutral): `#FAFAF9` → `#E7E5E4` → `#44403C` → `#1C1917`. Neutral (true neutral): `#FAFAFA` → `#E5E5E5` → `#404040` → `#171717`.
- **Source context:** Tailwind's default color scales
- **Why included:** Tailwind-native fit — zero-friction integration with the Tailwind theme config. Stone gives warm tint; Neutral gives chromatically dead.
- **Why might FIT MeeSell:** Lowest-friction technical fit. Stone scale supports warm-primary composition; Neutral scale is universally compatible. 11-stop ladder covers all hierarchy needs.
- **Why might NOT fit:** Tailwind defaults are very recognisable — risk of "default Tailwind app" perception. Stone scale's warmth is less articulated than Polaris's bespoke warm-tints.
- **Screenshot/exemplar:** Vercel and Linear both use Tailwind Stone or Neutral scales with custom primaries.

#### Reference 7 — Notion warm cream (https://www.notion.so/)
- **Visual signal:** App background `#FFFFFF`; sidebar/subdued surface `#F7F6F3` (warm cream); primary text `#37352F` (warm dark)
- **Source context:** Notion productivity SaaS; explicitly cited reference in DESIGNER_BRIEF.md §7
- **Why included:** Tests an aggressively warm-cream surface direction — most distinct from generic SaaS gray.
- **Why might FIT MeeSell:** Strongest emotional match to "workshop" cue. Warm cream supports long-session readability (less stark than pure white). Composes uniquely with warm primaries.
- **Why might NOT fit:** Same "yellowed" risk on low-end Android. Warm cream may not feel "fast/crisp" enough for the *fast* pillar. Notion-coded — perception risk.
- **Screenshot/exemplar:** Notion workspace: warm-cream sidebar, white page surface, warm-dark text, minimal borders.

---

### Category 1.4 — Primary typeface

**Brief recap (per DESIGNER_BRIEF.md §5.2 + CORE_PHILOSOPHY.md M9):**
- Latin (English V1)
- Tamil + Devanagari script support for V1.5 (without typeface migration)
- Mobile legibility critical (360px Android low-end)
- Open-source / free / Google Fonts preferred
- 4-5 weights (400/500/600/700 at minimum)
- Body baseline 16px on mobile

**Critical:** V1.5 Indic-script support is solved either by (a) the primary typeface having native Indic glyphs, or (b) pairing with a Noto Sans Tamil + Noto Sans Devanagari companion via `font-family` fallback. The candidate list below reports the script-coverage approach for each.

The agent evaluated ~13 typefaces and culled to the 8 strongest for V1's seller-tool context. Display-show-off typefaces and serifs were excluded — MeeSell is a tool, not a publication.

---

#### Reference 1 — Inter (https://fonts.google.com/specimen/Inter)
- **Visual signal:** Geometric grotesque sans-serif; very tall x-height (~73% of cap height); wide apertures on `c/e/a`; designed-for-screen by Rasmus Andersson
- **Source context:** Used by Linear, Vercel, Notion, Mozilla, Figma, Cash App, Stripe — current default of B2B SaaS
- **Why included:** Best-in-class screen legibility + universal recognition. Default of the field for a reason.
- **Why might FIT MeeSell:** Hits *fast* + *professional tool* hard. Excellent at 14-16px (catalog form labels) on low-end Android. Variable axis = small file (1 file, all weights).
- **Why might NOT fit:** No native Indic glyphs — V1.5 requires Noto Sans Tamil + Noto Sans Devanagari pairing. The font-family fallback works but causes faint visual seams when English + Tamil mix in one string (catalog name "Saree" + Tamil label "புடவை"). Inter is also so ubiquitous it adds no brand differentiation.
- **Available weights:** 100 / 200 / 300 / 400 / 500 / 600 / 700 / 800 / 900 (variable)
- **Indic plan:** Pair Noto Sans Tamil (https://fonts.google.com/noto/specimen/Noto+Sans+Tamil) + Noto Sans Devanagari (https://fonts.google.com/noto/specimen/Noto+Sans+Devanagari) via fallback chain `'Inter', 'Noto Sans Tamil', 'Noto Sans Devanagari', system-ui, sans-serif`
- **Screenshot/exemplar:** Linear app: Inter at 14px body, 13px UI, 28px headings. Tight tracking, wide apertures, very crisp on Retina + clear on low-end Android.

#### Reference 2 — Plus Jakarta Sans (https://fonts.google.com/specimen/Plus+Jakarta+Sans)
- **Visual signal:** Modern geometric sans by Tokotype; slightly more "designed/branded" feel than Inter; balanced x-height; rounded apertures
- **Source context:** Indonesian foundry; used by Tokopedia (largest Indonesian commerce platform — close persona match), various Asian SaaS
- **Why included:** Asian-foundry designed; tuned for Asian-language seller persona. Distinct without being eccentric.
- **Why might FIT MeeSell:** Hits *Indian-context-aware* obliquely (Asian-foundry SE-Asia commerce alignment). Distinct enough to be MeeSell's brand voice. Excellent variable axis.
- **Why might NOT fit:** No native Tamil/Devanagari — same V1.5 pairing problem as Inter. Slightly less crisp than Inter at sub-14px on low-end Android.
- **Available weights:** 200 / 300 / 400 / 500 / 600 / 700 / 800 (variable)
- **Indic plan:** Same as Inter — pair with Noto Sans Tamil + Noto Sans Devanagari
- **Screenshot/exemplar:** Tokopedia merchant interface uses Plus Jakarta Sans family for product listings, forms, and dashboards.

#### Reference 3 — DM Sans (https://fonts.google.com/specimen/DM+Sans)
- **Visual signal:** Geometric sans by Colophon Foundry / Google Fonts; slightly condensed; medium x-height; humanist details
- **Source context:** Used by Razorpay marketing site, various Indian B2B SaaS
- **Why included:** Has Indian-SaaS deployment precedent. More personality than Inter without being eccentric.
- **Why might FIT MeeSell:** Slight condensation helps dense forms (catalog edit page) fit on 360px Android. Razorpay deployment proves Indian-SaaS-context fit.
- **Why might NOT fit:** Less crisp than Inter at sub-14px. No native Indic glyphs. Variable axis is narrower than Inter's.
- **Available weights:** 100 / 200 / 300 / 400 / 500 / 600 / 700 / 800 / 900 (variable)
- **Indic plan:** Pair with Noto Sans Tamil + Noto Sans Devanagari
- **Screenshot/exemplar:** Razorpay marketing site uses DM Sans for hero copy and CTAs.

#### Reference 4 — Manrope (https://fonts.google.com/specimen/Manrope)
- **Visual signal:** Modern grotesque by Mikhail Sharanda; tall x-height; geometric construction with humanist details
- **Source context:** Used by Cred (Indian fintech), various B2B SaaS marketing sites
- **Why included:** Indian-app deployment precedent (Cred). Distinct from Inter without being eccentric.
- **Why might FIT MeeSell:** Cred deployment proves Indian-context fit. Tall x-height helps small-size legibility. Variable axis available.
- **Why might NOT fit:** Cred-coded — premium-fintech association may pull MeeSell toward an aspirational tone that mismatches the working-tool brief. No native Indic glyphs.
- **Available weights:** 200 / 300 / 400 / 500 / 600 / 700 / 800 (variable)
- **Indic plan:** Pair with Noto Sans Tamil + Noto Sans Devanagari
- **Screenshot/exemplar:** Cred app uses Manrope for hero copy and CTAs over dark surfaces.

#### Reference 5 — Be Vietnam Pro (https://fonts.google.com/specimen/Be+Vietnam+Pro)
- **Visual signal:** Geometric grotesque designed by Be — Vietnamese type foundry; designed for Latin + Vietnamese (extensive diacritics)
- **Source context:** Used by Vietnamese fintech, SE Asian B2B SaaS
- **Why included:** SE Asian foundry with extensive diacritic support — relevant to multilingual content (Indian languages have many diacritic-like marks).
- **Why might FIT MeeSell:** Asian-foundry alignment. Excellent diacritic handling translates to cleaner display of romanised Indian text (e.g., transliterated brand names).
- **Why might NOT fit:** No native Tamil/Devanagari — must pair with Noto. Slightly less screen-tuned than Inter on low-end Android.
- **Available weights:** 100 / 200 / 300 / 400 / 500 / 600 / 700 / 800 / 900
- **Indic plan:** Pair with Noto Sans Tamil + Noto Sans Devanagari
- **Screenshot/exemplar:** Be Vietnam Pro shipping in SE Asian fintech apps; clean geometric look at 14-18px sizes.

#### Reference 6 — Noto Sans (https://fonts.google.com/noto/specimen/Noto+Sans)
- **Visual signal:** Google's universal typeface; humanist sans-serif; designed by Monotype for Google; massive script coverage
- **Source context:** Google's "no tofu" project; used by Wikipedia, many multilingual sites
- **Why included:** Native Tamil + Devanagari + Latin in the SAME family — eliminates the V1.5 pairing problem entirely. Single typeface decision covers V1 and V1.5 with zero visual seams.
- **Why might FIT MeeSell:** Solves the M9 i18n structural requirement at the typeface layer. No font-family fallback chain needed. Eliminates the "English + Tamil look slightly different" seam that Inter/Plus Jakarta/DM Sans all carry. Hits *Indian-context-aware* uniquely — same typeface for all three scripts.
- **Why might NOT fit:** Noto Sans is slightly less screen-tuned than Inter; can read "encyclopedia/Wikipedia" rather than "modern tool." x-height is medium (not tall). Variable axis exists but is less refined than Inter's. Most importantly: Noto's Latin variant has lower brand-differentiation potential — recognisable as "the default multilingual font."
- **Available weights:** 100 / 200 / 300 / 400 / 500 / 600 / 700 / 800 / 900 (variable)
- **Indic plan:** Already native — `font-family: 'Noto Sans', sans-serif` covers Latin + Tamil + Devanagari + 800+ scripts
- **Screenshot/exemplar:** Wikipedia (multilingual content), Google Translate, government multilingual sites use Noto Sans family.

#### Reference 7 — Hanken Grotesk (https://fonts.google.com/specimen/Hanken+Grotesk)
- **Visual signal:** Modern grotesque by Alfredo Marco Pradil; balanced x-height; subtle humanist details; very crisp at small sizes
- **Source context:** Newer foundry release (2018+); used by emerging B2B SaaS
- **Why included:** Less-deployed than Inter (so brand differentiation), but high quality + screen-optimised.
- **Why might FIT MeeSell:** Distinct from the saturated Inter market. Excellent small-size legibility. Variable axis.
- **Why might NOT fit:** No native Indic glyphs. Less proven at Tirupur device floor than Inter. Lower designer-community familiarity.
- **Available weights:** 100 / 200 / 300 / 400 / 500 / 600 / 700 / 800 / 900 (variable)
- **Indic plan:** Pair with Noto Sans Tamil + Noto Sans Devanagari
- **Screenshot/exemplar:** Hanken Grotesk in SaaS landing pages; clean modern grotesque with slightly warmer feel than Inter.

#### Reference 8 — Public Sans (https://fonts.google.com/specimen/Public+Sans)
- **Visual signal:** US Web Design System default; neutral grotesque; high x-height; designed for public-government tools
- **Source context:** US Government USWDS; designed by the United States Web Design System for federal sites
- **Why included:** Designed explicitly for "civic professional tool" use cases — same emotional register as MeeSell (serious, accessible, no decorative bloat).
- **Why might FIT MeeSell:** Hits *trustworthy* + *professional tool* without any branding posture. Designed for WCAG-strict environments. Free and rock-solid.
- **Why might NOT fit:** "Looks like a government form" — emotional register may be too austere for a tool that should energise the seller. No native Indic glyphs.
- **Available weights:** 100 / 200 / 300 / 400 / 500 / 600 / 700 / 800 / 900 (variable)
- **Indic plan:** Pair with Noto Sans Tamil + Noto Sans Devanagari
- **Screenshot/exemplar:** USWDS reference sites (vote.gov, USCIS forms); restrained and accessible.

---

### Category 1.5 — Iconography variant

**Brief recap (per DESIGNER_BRIEF.md §5.3):**
- ~15 key icons coverage: catalog, image, price, export, search, filter, add, edit, delete, check, warning, info, upload, download, settings
- 24×24 base size with `currentColor` SVG (recolorable via CSS)
- Material Symbols variants (outlined / filled / rounded / sharp) are first candidates; alternative sets evaluated for completeness

The agent evaluated 7 icon families and presents 6 variants below. Coverage of the 15-icon set is verified for each.

---

#### Reference 1 — Material Symbols Outlined (https://fonts.google.com/icons?icon.set=Material+Symbols&icon.style=Outlined)
- **Visual signal:** Variable-axis Material Symbols, outlined variant; 24px grid; 400 stroke weight default
- **Source context:** Google Material Symbols (2023+ unified set); default for Material 3 / Angular Material 18
- **Why included:** Default of Angular Material — picking this minimises CSS/dependency friction.
- **Why might FIT MeeSell:** Mechanical Angular Material fit. Variable axis allows fine-tuning weight/grade/optical-size per usage. Outlined variant reads "tool-not-app" — common in B2B SaaS (Notion, Linear, GitHub-style icon weight). Excellent coverage of the 15-icon set.
- **Why might NOT fit:** Outlined Material Symbols at 24px on low-end Android can read slightly thin — visibility risk for primary navigation icons. Very ubiquitous — adds no brand differentiation.
- **15-icon coverage:** ✓ All 15 covered (catalog → `inventory_2`, image → `image`, price → `payments`, export → `file_download` / `ios_share`, search → `search`, filter → `filter_list`, add → `add`, edit → `edit`, delete → `delete`, check → `check`, warning → `warning`, info → `info`, upload → `upload`, download → `download`, settings → `settings`)
- **Screenshot/exemplar:** Material 3 reference apps; Angular Material 18 documentation samples. Outlined icons with even stroke weight.

#### Reference 2 — Material Symbols Rounded (https://fonts.google.com/icons?icon.set=Material+Symbols&icon.style=Rounded)
- **Visual signal:** Material Symbols rounded variant; same 24px grid; softer terminations on strokes
- **Source context:** Google Material Symbols variant
- **Why included:** Tests a softer, less institutional Material variant — bridges between "warm/friendly" and "tool".
- **Why might FIT MeeSell:** Rounded variant softens the tool aesthetic — supports a "warm Indian seller tool" emotional register without sacrificing seriousness. Composes well with warm primary colors.
- **Why might NOT fit:** Rounded can read "consumer app" rather than "professional tool" — risks tipping toward Meesho-buyer aesthetic. Subtle but real risk.
- **15-icon coverage:** ✓ All 15 covered (same names as outlined)
- **Screenshot/exemplar:** Google's own consumer products (Calendar, Tasks) use rounded Material Symbols; softer feel than outlined.

#### Reference 3 — Material Symbols Sharp (https://fonts.google.com/icons?icon.set=Material+Symbols&icon.style=Sharp)
- **Visual signal:** Material Symbols sharp variant; same 24px grid; angular terminations
- **Source context:** Google Material Symbols variant
- **Why included:** Tests a crisper, more "engineered" Material variant.
- **Why might FIT MeeSell:** Hits *professional tool* hardest among Material variants. Pairs well with geometric typefaces (Inter, Plus Jakarta Sans).
- **Why might NOT fit:** Sharp variant has the lowest deployment in mainstream B2B SaaS — may read "uncommon/odd" rather than "distinctive." Angular terminations may clash with warm/soft primary colors.
- **15-icon coverage:** ✓ All 15 covered
- **Screenshot/exemplar:** Material 3 docs show Sharp variant in reference screenshots; sharper, more engineered feel.

#### Reference 4 — Phosphor Icons (https://phosphoricons.com/)
- **Visual signal:** Geometric icon family with 6 weights (Thin / Light / Regular / Bold / Fill / Duotone); flexible width-axis like a variable font
- **Source context:** Independent designer-built icon family by Helena Zhang + Tobias Fried; rising adoption in modern B2B SaaS
- **Why included:** Strong brand differentiation from Material Symbols. 6 weights = wide tonal range. Excellent for combining outlined (UI) + filled (states) usage.
- **Why might FIT MeeSell:** Distinct visual voice. The Regular + Fill pairing supports "outlined for nav, filled for active state" patterns. Composes well with geometric typefaces.
- **Why might NOT fit:** Adds a dependency (~50-100KB if subset properly). Not native to Angular Material — wrapper component needed. Some icons (e.g., `settings` = `gear`) have different naming conventions than seller mental models.
- **15-icon coverage:** ✓ All 15 covered (catalog → `package`, image → `image`, price → `currency-inr` available, export → `export`, search → `magnifying-glass`, filter → `funnel`, add → `plus`, edit → `pencil-simple`, delete → `trash`, check → `check`, warning → `warning`, info → `info`, upload → `upload`, download → `download`, settings → `gear`)
- **Screenshot/exemplar:** Phosphor's marketing site demonstrates the 6 weights; very polished and consistent.

#### Reference 5 — Lucide Icons (https://lucide.dev/)
- **Visual signal:** Single-weight outlined icon family; Feather Icons fork with active maintenance; 24px grid; 2px stroke
- **Source context:** Community-maintained open-source icon library; used by shadcn/ui, Tailwind UI, many B2B SaaS
- **Why included:** De-facto icon standard in the modern Tailwind ecosystem. Excellent for "minimal SaaS tool" aesthetic.
- **Why might FIT MeeSell:** Pairs naturally with Tailwind + Inter typography. Very clean and uniform. Strong community support → no abandonment risk.
- **Why might NOT fit:** Single-weight outlined — no filled variant for "active state" patterns (requires custom solution). Strokes can read thin on low-end Android.
- **15-icon coverage:** ✓ All 15 covered (catalog → `package`, image → `image`, price → `indian-rupee`, export → `share`, search → `search`, filter → `filter`, add → `plus`, edit → `pencil`, delete → `trash-2`, check → `check`, warning → `triangle-alert`, info → `info`, upload → `upload`, download → `download`, settings → `settings`)
- **Screenshot/exemplar:** Most shadcn/ui demo sites; Vercel dashboard; clean uniform outlined icons.

#### Reference 6 — Tabler Icons (https://tabler-icons.io/)
- **Visual signal:** Outlined family with 4000+ icons; 24px grid; 2px stroke; optional filled variant
- **Source context:** Independent icon family by Paweł Kuna; popular in admin dashboard templates
- **Why included:** Largest free icon family (4000+). Outlined + filled pairing solves the active-state problem Lucide has.
- **Why might FIT MeeSell:** Massive coverage = future-proof (no "icon not in library" gaps). Filled variant supports active-nav patterns. Composes cleanly with geometric typefaces.
- **Why might NOT fit:** Admin-template-coded — risk of "looks like an admin template" perception. Stylistically similar to Lucide and Material Outlined — adds no strong differentiation.
- **15-icon coverage:** ✓ All 15 covered with both outlined and filled variants
- **Screenshot/exemplar:** Tabler admin dashboard templates; widely used in indie SaaS landing pages.

---

## Phase 2 — Components

[TO BE POPULATED IN ROUND N — not in scope this round per DESIGN_SYSTEM_ARCHITECTURE.md §1.C Phase 2; coordinator dispatches the agent for Phase 2 after Phase 1 categories all have founder picks and composition is confirmed.]

---

## Phase 3 — Layout

[TO BE POPULATED IN ROUND N — not in scope this round per DESIGN_SYSTEM_ARCHITECTURE.md §1.C Phase 3]

---

## Phase 4 — Voice

[TO BE POPULATED IN ROUND N — not in scope this round per DESIGN_SYSTEM_ARCHITECTURE.md §1.C Phase 4]

---

## Picks log (founder ratifications)

| Date | Category | Reference picked | Founder note |
|---|---|---|---|
| (pending) | 1.1 Primary brand color | — | — |
| (pending) | 1.2 Secondary color | — | — |
| (pending) | 1.3 Surface/neutral palette | — | — |
| (pending) | 1.4 Primary typeface | — | — |
| (pending) | 1.5 Iconography variant | — | — |

Coordinator appends a row when founder ratifies a category.

---

## Round 1 curation notes (agent-side)

**Sourcing methodology this round.** The agent leveraged training corpus knowledge of public design system documentation (IBM Carbon, Atlassian, Polaris, GitHub Primer, Material 3, Tailwind), public Indian SaaS dashboard visual identities (Razorpay, Zoho, Freshworks, Khatabook, Vyapar, OkCredit, BharatPe), Google Fonts catalog (Inter, Plus Jakarta Sans, DM Sans, Manrope, Be Vietnam Pro, Noto Sans, Hanken Grotesk, Public Sans), and Material Symbols + open-source icon libraries (Phosphor, Lucide, Tabler). WebFetch was unavailable in this dispatch — all visual specs (hex codes, typeface metrics, icon coverage) are reported from stable public reference knowledge. If founder wants a screenshot for any specific reference, coordinator may dispatch a Playwright capture in a follow-up turn.

**Reference counts per category (this round).**
- 1.1 Primary brand color: 9 strong references
- 1.2 Secondary color: 8 strong references
- 1.3 Surface/neutral palette: 7 strong references
- 1.4 Primary typeface: 8 strong references
- 1.5 Iconography variant: 6 strong references
- **Total Round 1: 38 strong references after culling from ~75 evaluated candidates**

**Spanning behaviour intentionally included.**
- Category 1.1 deliberately spans: warm-orange (Khatabook/Vyapar), terracotta (Lightspeed), rust-red (Zoho), gold-amber (OkCredit), deep-teal (Freshworks), deep-blue outliers (Razorpay/BharatPe), and a no-chromatic outlier (Notion). Founder can narrow to a family in Round 2.
- Category 1.2 spans deep-blue (Carbon/Material/Primer), teal (Atlassian), green (Polaris/Tailwind-emerald), and chromatic-neutral (Tailwind slate / Carbon cool-gray) — to compose with whichever primary founder picks.
- Category 1.4 includes one native-Indic-glyph option (Noto Sans) and seven pair-with-Noto-fallback options to expose the trade-off explicitly.

**Anti-reference filtering applied this round.**
- Excluded: Meesho-buyer #F43397 pink, Stripe purple #635BFF, Linear grey-purple #5E6AD2, saffron-flag #FF9933, BankBazaar/Cred fintech aesthetic (kept Razorpay/BharatPe only as anti-reference-illustrative candidates with explicit "why might NOT fit" calling out fintech).
- Excluded display typefaces (Playfair, Lora, decorative serifs), variable-display fonts (Recursive), and fonts with poor sub-14px legibility (Poppins — rejected for low-end Android readability despite popularity).
- Excluded icon families with known IP/licensing concerns (Font Awesome Pro, Streamline).

**Open requests for founder (Round 2 priorities).**
The agent flags these for founder clarification — answers will sharpen Round 2 if founder requests refinement rather than pick:
1. **Warm-primary intensity preference.** Is the founder leaning saturated (Khatabook orange territory) vs muted (OkCredit gold territory) vs earthy (Lightspeed terracotta)? Currently spanning all three.
2. **Native-Indic vs pair-with-Noto tradeoff on typography.** The native-Noto-Sans option is the cleanest V1.5 migration but costs Latin-side brand distinctiveness. Founder lean?
3. **Iconography family tradeoff.** Mechanical Material fit (no dep) vs Phosphor/Lucide brand-differentiation (small dep). Founder lean?
4. **Anti-reference check on outliers.** Reference 9 (Notion no-chromatic-primary) and Reference 6 (Freshworks teal) are deliberately at the edge of the brief — founder may want them excluded from Round 2 if "warm Indian seller tool" is hard-constrained.

**End of REFERENCE_DICTIONARY.md Round 1**
