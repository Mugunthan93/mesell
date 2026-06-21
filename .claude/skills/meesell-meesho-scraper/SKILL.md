---
name: meesell-meesho-scraper
description: >-
  MeeSell's conventions for the Playwright-based Meesho catalogue scraper that refreshes the
  category tree and brand whitelist quarterly. Use this skill WHENEVER you are creating or
  editing the scraper, its snapshot diffing, schema-change detection, rate limiting, or
  robots/ToS-respecting behavior — even if the user only says "scrape Meesho", "refresh the
  category data", "the scraper broke", or "detect category changes". Do NOT use it for parsing
  the resulting XLSX/snapshot into JSON (defer to meesell-xlsx-category-parser) or the picker
  that consumes the data (defer to meesell-category-picker-pipeline).
---

# MeeSell Meesho Scraper Conventions

These are the locked rules for the quarterly Meesho scrape. They exist so the refresh is
polite, resilient to Meesho's UI changes, and produces a reviewable diff rather than a silent
data swap. They derive from `CLAUDE.md` data-pipeline scope (Feature 3 / quarterly refresh) and
the project's reference-data design, which win.

## The non-negotiables (and why each matters)

- **Rate-limited and robots/ToS-respecting.** Throttle requests, add human-like delays, respect
  `robots.txt`, and never hammer Meesho. This is a low-frequency quarterly job — there is no
  reason to move fast. Aggressive scraping risks an IP block and the data source we depend on.

- **Snapshot, then diff — never overwrite blindly.** Each run writes a timestamped snapshot and
  produces a diff against the previous snapshot (added/removed/renamed categories, changed
  attributes). The data-engineer reviews the diff before it's promoted. A blind overwrite can
  silently delete categories sellers are mid-catalog on.

- **Schema-change detection is a first-class output.** If Meesho moves a column, renames a field,
  or changes the page structure, the scraper must DETECT and report it (not crash, not silently
  mis-map). A "structure changed" alert is the whole point of running this — it's the early
  warning that downstream parsing needs an update.

- **Idempotent + resumable.** A run that dies partway can be re-run without corrupting the
  snapshot. Write to a temp snapshot and atomically promote on success; never leave a partial
  snapshot as the latest.

- **Selectors are centralized and defensive.** Keep CSS/XPath selectors in one place with a
  fallback strategy; a brittle inline selector scattered through the code makes every Meesho
  tweak a multi-file fix. Fail with a clear "selector X no longer matches" message.

- **Quarterly cadence, off-peak, headless.** Run on a schedule (not ad-hoc), headless, with
  retries and a dead-letter alert if it can't complete — surfaced to the data-engineer.

## Run shape

```
schedule (quarterly)
  │
  ▼  navigate Meesho category pages (rate-limited, robots-checked, human-like delays)
  ▼  extract tree + attributes + brand list via centralized selectors
  ▼  write timestamped snapshot to a TEMP location
  ▼  schema-change detection: compare structure vs previous snapshot
  │     └─ structure changed ──► ALERT data-engineer; do NOT auto-promote
  ▼  content diff vs previous snapshot (added/removed/renamed)
  ▼  atomically promote temp -> latest ONLY on a clean run
  ▼  hand snapshot to meesell-xlsx-category-parser for normalization
```

## Politeness defaults

```python
# Conservative, quarterly job — favor safety over speed.
RATE_LIMIT_RPS = 0.5            # ~1 request every 2s, plus jitter
PER_REQUEST_JITTER = (0.5, 2.0) # random extra delay range (seconds)
RESPECT_ROBOTS = True
MAX_RETRIES = 3                 # exponential backoff; dead-letter alert on exhaustion
```

## Quick checklist before you finish a scraper task

- [ ] Rate-limited + jittered; `robots.txt`/ToS respected; quarterly, not aggressive
- [ ] Writes a timestamped snapshot; produces a reviewable diff vs the previous one
- [ ] Schema/structure changes DETECTED and alerted, not crashed or silently mis-mapped
- [ ] Idempotent/resumable; temp-then-atomic-promote; no partial "latest"
- [ ] Selectors centralized with a fallback + clear "selector no longer matches" error
- [ ] Scheduled, headless, retries + dead-letter alert to the data-engineer
- [ ] Output handed to the XLSX parser, not normalized here
