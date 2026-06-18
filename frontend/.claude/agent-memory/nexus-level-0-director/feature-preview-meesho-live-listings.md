---
name: feature-preview-meesho-live-listings
description: "PREVIEW FEATURE REDEFINED (founder 2026-06-18). The old /catalogs/:id/preview pre-publish mockup-wiring plan is OBSOLETE. Real feature = 'My Live Listings': seller uploads their own Meesho Inventory-Update-File XLSX → we generate 'View on Meesho' public deep-links via base36(product_id). V1=(a) standalone view only; (b) match-into-catalogs deferred to V2. NEVER scrape in prod (ban)."
metadata:
  node_type: memory
  type: project
---

# Preview feature = "My Live Listings" (View-on-Meesho deep-links)

Founder ruling, 2026-06-18. Supersedes the earlier frontend-coordinator "Option B" preview-wiring SPEC (that wired the old simulated `/catalogs/:id/preview` mockup to `GET /products/{id}/preview` — now OBSOLETE). The product the founder actually wants: let a seller see their approved products as they appear on the **public Meesho consumer site** (which the supplier panel does not show), via a **"View on Meesho"** deep-link.

## The base36 discovery (VERIFIED LIVE 2026-06-18)
Public Meesho PDP URL = `https://www.meesho.com/{slug}/p/{base36(product_id)}`.
- The `/p/<id>` segment is the internal numeric `product_id` encoded in **base36** (alphabet `0-9a-z`, pure, no salt/offset). Decode = `int(seg, 36)`.
- **The slug is COSMETIC** — any slug resolves; `/x/p/<id>` works. So `product_id` alone is sufficient; the slug is just `slugify(name)` for SEO/readability.
- Proof: `base36(494492882)="86ep5e"` (a real PDP the founder found) and `base36(698442056)="bju1c8"` → `https://www.meesho.com/x/p/bju1c8` rendered the REAL Curl Candy product 698442056 (image CDN path keys on the exact product_id; title/seller matched). Negative control: an unknown id returns a soft-404 "Not Found page" — distinguishable by TITLE/CONTENT, not by HTTP status (always 200).
- **Building the URL needs ZERO network** (pure arithmetic) → no ban risk at all. Earlier round-1/2 "/p/698442056" 404 was a red herring (decimal, not base36).

## Production input = seller's OWN export (NO SCRAPING)
**Why:** founder ruled scraping in production WILL get us banned by Meesho. Scraping was used ONLY for the feasibility spikes on the founder's own account. base36 adds no new data-access surface (pure transform of an id the seller gives us).
**How:** the seller downloads their own **"Inventory Update File"** XLSX from the Meesho supplier panel and uploads it to MeeSell. Verified columns (sheet `Inventory-Update-Data-Fill This`, **2 header rows** then data):
`SERIAL NO | CATALOG NAME | CATALOG ID | PRODUCT NAME | PRODUCT ID | STYLE ID(=SKU) | VARIATION ID | VARIATION | STOCK | SYSTEM STOCK COUNT | YOUR STOCK COUNT`.
We need only **PRODUCT ID** (→ base36) + **PRODUCT NAME** (→ slug). Confirmed: SKU `HBC-DR-NG-P2` row → PRODUCT ID `698442056`. ~15 product rows for the test account (store "Curl Candy", supplier 3661229, login 8220476727).

## Scope decision
- **V1 = (a) standalone "My Live Listings" view**: upload file → parse → table of products with "View on Meesho" links. Does NOT need to match MeeSell's own catalog records.
- **(b) match export rows into existing MeeSell catalogs (by SKU/Style ID) → attach link to the product in current catalog views = DEFERRED to V2.**

## How to apply
- When building/replanning the preview feature: build (a) only; core = xlsx parse (PRODUCT ID + PRODUCT NAME) + `base36(id)` util + `slugify(name)` + "View on Meesho" button. Likely doable client-side (SheetJS + JS base36) → possibly frontend-only/no-persistence for V1; confirm persistence need with founder.
- Only `meesell-*` agents. The old preview-wiring SPEC must NOT be implemented as-was.
- NEVER scrape Meesho in production. macOS note: screenshots in NSIRD/temp/Desktop are TCC-unreadable by agents — get files dropped inside the project tree or via ~/Downloads (Downloads WAS readable).
