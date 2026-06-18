# Mesell — Figma Design Setup Guide

**Branch:** worktree-design-figma-ui-screens (isolated from develop)
**Goal:** Design all Mesell app screens using PrimeNG component library + Mesell brand tokens

---

## Step 1 — Create the Figma File

1. Open figma.com → New design file
2. Name it: **Mesell UI — App Screens**
3. Set up pages:
   - `🎨 Tokens` (variables live here)
   - `📐 Components` (PrimeNG component library)
   - `01 Dashboard`
   - `02 Catalog Preview`
   - `03 Quality Check`
   - `04 Price Calculator`
   - `05 Export`
   - `06 Catalog Form`

---

## Step 2 — Install Plugins

Install both from Figma Community (free):

| Plugin | Purpose |
|---|---|
| **Tokens Studio for Figma** | Imports `mesell-tokens.tokens.json` → creates Figma Variables |
| **PrimeUI Theme Generator** | Reads those variables → generates PrimeNG component library |

---

## Step 3 — Import Mesell Tokens (Tokens Studio)

1. Open **Tokens Studio** plugin
2. Go to **Settings** → choose **Local file / JSON** as provider
3. Load `figma/mesell-tokens.tokens.json` from this repo
4. Click **Apply all tokens**
5. Tokens Studio creates Variable Collections:
   - `global/color/primary` (orange scale)
   - `global/color/brand`
   - `global/color/surface`
   - `global/color/semantic`
   - `global/typography`
   - `global/spacing`
   - `global/borderRadius`
   - `global/boxShadow`

---

## Step 4 — Run PrimeUI Theme Generator

1. Open **PrimeUI Theme Generator** plugin
2. Plugin detects the Variable Collections from Step 3
3. Map the collections to PrimeNG semantic tokens:

   | PrimeNG Token | Mesell Variable |
   |---|---|
   | Primary color | `global/color/primary/500` → `#F26B23` |
   | Surface 0 (white) | `global/color/surface/0` → `#ffffff` |
   | Surface 50 | `global/color/surface/50` → `#f0f5f9` |
   | Surface 900 (text) | `global/color/surface/900` → `#2a3547` |

4. Select **Aura** preset (matches `theme.ts` MeeSellPreset which extends Aura)
5. Click **Generate** → plugin creates PrimeNG component frames in `📐 Components` page

---

## Step 5 — Design the Screens

Use the generated PrimeNG components to design each screen.
Reference the component patterns from the live app at `localhost:4200`.

### Screen specs

#### 01 Dashboard
- Frame: 1440×900 (desktop) + 390×844 (mobile)
- Layout: Left sidebar 260px (navy `#111c2d`) + main content area
- Sidebar: Logo, nav groups (Home / Catalogs / Categories / Account), avatar
- Main: Page header, catalog count stat cards, recent catalogs list (p-dataView)
- CTA: `+ New Catalog` button (pill, orange `#F26B23`)

#### 02 Catalog Preview
- Frame: 1440×900 + 390×844
- Layout: Split — left 40% (SKU list sidebar) + right 60% (Meesho listing preview)
- Preview panel: Mimics Meesho product page layout (image, title, price, specs)
- Actions bar: Edit / Quality Check / Export buttons

#### 03 Quality Check
- Frame: 1440×900 + 390×844
- Layout: Score card header (big circular score) + issue list
- Score circle: Colour-coded (green ≥80, amber 60–79, red <60)
- Issue list: p-accordion per category (Title / Description / Images / Fields)
- Each issue: severity badge (error/warning/info) + fix suggestion

#### 04 Price Calculator
- Frame: 1440×900 + 390×844
- Layout: Left panel — inputs (selling price, GST %, commission %) | Right panel — P&L breakdown
- P&L card: Revenue / Commission / GST / Shipping / Net Margin — colour-coded
- Min viable price indicator strip (orange line at breakeven)

#### 05 Export
- Frame: 1440×900 + 390×844
- Layout: Catalog summary card + export options (CSV / ZIP with images)
- Status: Progress bar (p-progressBar, orange) while generating
- Download button: Pill, orange, large

#### 06 Catalog Form (Wizard)
- Frame: 390×844 (mobile-first — primary use case is phone)
- Layout: Step indicator (p-steps) + form content + Next/Back nav
- Steps: Category → Product Details → Images → Pricing → Review

---

## Step 6 — Export Specs Back to Repo

After designs are approved:
1. Export each screen as PNG 2x into `figma/exports/`
2. Export component specs as PDF into `figma/specs/`
3. Open a PR from `worktree-design-figma-ui-screens` → `develop`
4. Founder approves → meesell-frontend-coordinator implements

---

## Brand Reference (quick copy)

```
Primary orange:  #F26B23
Navy sidebar:    #111c2d
Page bg:         #f0f5f9
Card surface:    #ffffff
Body text:       #2a3547
Muted text:      #5a6a85
Error:           #DC2626
Success:         #16A34A
Warning:         #D97706
Info:            #2563EB
Font:            Plus Jakarta Sans
Button radius:   999px (pill)
Card radius:     16px
Input radius:    7px
```
