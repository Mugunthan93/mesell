# PrimeNG.org — Full Website Scrape (section-wise)

**Scraped:** 2026-06-16
**Sidebar map:** `docs/primeng/menu-list.html` (the live left-nav, authoritative — every section below maps to it)
**Pages captured:** 121 markdown files (~2.1 MB) across all 14 sidebar sections

**Two source methods** (because primeng.org is a client-rendered SPA):
1. **LLM markdown export** — `https://primeng.org/llms/components/<name>.md` and `/llms/pages/<name>.md`. Clean, official markdown. Covers every documentation page (sections 00–07).
2. **GitHub showcase source** — `github.com/primefaces/primeng/apps/showcase`. The marketing/tool sections (08–13) have NO llms export, so their prose was extracted from the Angular template strings in the repo and converted to markdown.

> Complementary to the sibling `docs/primeng/*.md` files (generated from the installed package's `.d.ts` — imports/selectors/signatures). Use this `_site/` tree for website prose, usage examples, accessibility & API; use the parent `*.md` for exact API truth.

---

## Section structure (all 14 sidebar sections)

| # | Section | Pages | Method | Folder |
|---|---------|-------|--------|--------|
| 00 | Getting Started | 2 | llms | `00-getting-started/` — installation, configuration |
| 01 | Theming | 3 | llms | `01-theming/` — styled, unstyled, tailwind |
| 02 | AI Tools | 2 | llms | `02-ai-tools/` — llms, mcp |
| 03 | **Components** | 92 | llms | `03-components/` — see groups below |
| 04 | Pass Through | 1 | llms | `04-passthrough/` — passthrough |
| 05 | Guides | 3 | llms | `05-guides/` — accessibility, animations, rtl |
| 06 | Icons | 2 | llms | `06-icons/` — icons, customicons |
| 07 | Migration | 3 | llms | `07-migration/` — v21, v20, v19 |
| 08 | Figma UI Kit | 3 | repo | `08-figma-uikit/` — overview, guide-v4, guide-v3 |
| 09 | Theme Designer | 3 | repo | `09-theme-designer/` — overview, guide, ci-pipeline |
| 10 | Templates | 1 | repo | `10-templates/` — index (gallery of 10 templates + preview links) |
| 11 | PrimeBlocks | 1 | external | `11-primeblocks/` — README (external product note) |
| 12 | Support | 2 | repo | `12-support/` — long-term-support, pro-support |
| 13 | Discover | 3 | repo | `13-discover/` — about-us, roadmap, contribution |
| | **TOTAL** | **121** | | |

### Components (92) — grouped exactly as the sidebar

| Group | Count | Folder |
|-------|-------|--------|
| Form | 28 | `03-components/form/` |
| Button | 3 | `03-components/button/` |
| Data | 10 | `03-components/data/` (virtualscroller served as `scroller.md`) |
| Panel | 10 | `03-components/panel/` |
| Overlay | 7 | `03-components/overlay/` |
| File | 1 | `03-components/file/` |
| Menu | 8 | `03-components/menu/` |
| Chart | 1 | `03-components/chart/` |
| Messages | 2 | `03-components/messages/` |
| Media | 4 | `03-components/media/` |
| Misc | 18 | `03-components/misc/` |

---

## Remaining gaps — 3 component pages have NO retrievable doc content

These return the SPA shell from `/llms/` **and** have no prose in the repo source (all `NEW`/utility entries — content exists only rendered in the live SPA):

| Page | Sidebar group | Notes |
|------|---------------|-------|
| `/bind` | Components → Misc | NEW-tagged, no markdown export, no repo prose |
| `/classnames` | Components → Misc | NEW-tagged, no markdown export, no repo prose |
| `/filterservice` | Components → Utilities | service API page, no markdown export |

## Notes on the repo-sourced sections (08–13)

- **Templates (10)** is a visual gallery — no long-form prose per template on primeng.org; each card links to a live preview site (captured in `index.md`). The per-template repo subdirs are logo components only.
- **PrimeBlocks (11)** is a separate commercial product (primeblocks.org), an external sidebar link, not a primeng.org doc page — captured as a short note.
- **External links** intentionally not scraped: PrimeTV (YouTube), Figma Plugin, Discord, Forum, Source Code, Changelog, Store, Twitter, Newsletter, PrimeGear, `/guides/primeflex` (PrimeFlex is a separate library), `/playground` (interactive tool).

---

## Re-scrape

```bash
# Sections 00–07 (llms markdown):
bash $CLAUDE_JOB_DIR/tmp/scrape.sh <repo-root>
# Sections 08–13 (repo-sourced): $CLAUDE_JOB_DIR/tmp/extract.py + fix.py
```

Full fetch manifest with HTTP codes + byte sizes for sections 00–07: `_manifest.tsv`.
