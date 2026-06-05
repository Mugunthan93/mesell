# Playwright MCP Capability Reference

**Status**: Authoritative reference for browser automation in the `mesell` project.
**Primary use case**: Meesho supplier panel scraping (category enumeration, bulk-upload template harvesting, single-upload form introspection).
**Scope**: Documents all 23 Playwright MCP tools exposed to Claude Code, their behavior, limitations, and battle-tested usage patterns.

This document is the contract. If MCP tool behavior diverges from what is described here, update this document before changing scraper code.

---

## Table of Contents

1. [Tool Inventory by Category](#1-tool-inventory-by-category)
2. [Critical Gaps and Quirks](#2-critical-gaps-and-quirks)
3. [Battle-Tested Patterns](#3-battle-tested-patterns)
4. [Concrete Code Snippets](#4-concrete-code-snippets)
5. [Workflow Mapping for Meesho Supplier Panel Scraping](#5-workflow-mapping-for-meesho-supplier-panel-scraping)
6. [Security and Responsible Use](#6-security-and-responsible-use)

---

## 1. Tool Inventory by Category

The 23 tools group into 7 functional categories. The split matters because tools in different categories have different failure modes (e.g., sensing tools never mutate page state; user-input tools always do).

### 1.1 Navigation and Lifecycle (5 tools)

These tools control the browser session — opening URLs, switching tabs, controlling viewport.

| Tool | Purpose | Notable Behavior |
|------|---------|------------------|
| `mcp__playwright__browser_navigate` | Go to a URL in the current tab | Waits for `load` event by default. URL must be fully qualified (include `https://`). |
| `mcp__playwright__browser_navigate_back` | Browser back button | No-op if there is no history. Does not return data — re-snapshot after to confirm landing page. |
| `mcp__playwright__browser_close` | Close the current page (tab) | If it is the last tab, the browser may shut down depending on MCP server config. |
| `mcp__playwright__browser_tabs` | List, create, close, or select tabs | Operations: `list`, `new`, `close`, `select`. Use `select` with index from `list`. Each tab has its own snapshot context. |
| `mcp__playwright__browser_resize` | Set viewport dimensions | Width and height in CSS pixels. Forces re-layout. Useful for testing responsive breakpoints or coaxing mobile-only menus to render. |

### 1.2 Sensing and Reconnaissance (5 tools)

These tools observe the page without mutating it. They are safe to call repeatedly and are the foundation for every other tool call (especially `browser_snapshot`, which produces the `[ref=eXX]` handles used by user-input tools).

| Tool | Purpose | Notable Behavior |
|------|---------|------------------|
| `mcp__playwright__browser_snapshot` | Accessibility tree dump with `[ref=eXX]` element IDs | Refs are stable handles within a single turn — see Section 2 for why they go stale. Output is YAML-like, role-based, similar to a screen reader's view. This is the only source of refs for action tools. |
| `mcp__playwright__browser_take_screenshot` | PNG or JPEG capture | Options: viewport-only or full-page; can target a single element by ref. Screenshots are for human evidence — they cannot drive subsequent actions. |
| `mcp__playwright__browser_console_messages` | Returns JS console output buffered since page load | Levels: `error`, `warning`, `info`, `debug`, `log`. Useful for detecting client-side validation failures, CSP violations, hydration errors. |
| `mcp__playwright__browser_network_requests` | Numbered list of network requests since load | Supports regex filter on URL. Returns: index, method, URL, status, resource type. Use index to drill into one request. |
| `mcp__playwright__browser_network_request` | Full headers + body of one request by index | Index from `browser_network_requests`. Returns request headers, request body, response headers, response body. The fastest way to discover an undocumented API. |

### 1.3 Synchronization (1 tool)

| Tool | Purpose | Notable Behavior |
|------|---------|------------------|
| `mcp__playwright__browser_wait_for` | Wait for text to appear, text to disappear, or N seconds | Exactly one of: `text` (wait for appearance), `textGone` (wait for removal), `time` (sleep). Default timeout is ~30s. Prefer text-based waits over time-based — they are deterministic. |

### 1.4 User Input Simulation (8 tools)

These tools mutate the page. They consume refs from `browser_snapshot`. If a ref is stale (DOM mutated since the snapshot), the call fails.

| Tool | Purpose | Notable Behavior |
|------|---------|------------------|
| `mcp__playwright__browser_click` | Mouse click | Buttons: `left`, `right`, `middle`. Modifiers: `Control`, `Shift`, `Alt`, `Meta` (Cmd on macOS), `ControlOrMeta`. Supports `doubleClick: true`. |
| `mcp__playwright__browser_type` | Type into editable element | `slowly: true` dispatches per-keypress JS events (needed for autocomplete widgets); `slowly: false` (default) pastes the whole string. `submit: true` appends Enter after. |
| `mcp__playwright__browser_fill_form` | Bulk-fill multiple fields atomically | Supports `textbox`, `checkbox`, `radio`, `combobox`, `slider`. Single tool call, all fields filled in one round-trip. Prefer this over multiple `browser_type` calls. |
| `mcp__playwright__browser_select_option` | Select native `<select>` option(s) | Pass values as an array. Multi-select supported if the element allows it. Does NOT work on custom dropdowns (React-Select, Headless UI Combobox) — those need `browser_click` + `browser_click` on the option. |
| `mcp__playwright__browser_press_key` | Single keypress | Examples: `Enter`, `Escape`, `ArrowDown`, `Tab`, `PageDown`. For modified keys use `browser_click` with modifiers or `browser_run_code_unsafe`. |
| `mcp__playwright__browser_hover` | Mouse hover | Reveals hover-only UI: dropdown menus, tooltips, "actions" columns in tables. Often a prerequisite for `browser_click` on menu items. |
| `mcp__playwright__browser_drag` | Drag between two elements | Source and target refs both required. Used for reorderable lists, drag-to-trash, kanban boards. |
| `mcp__playwright__browser_drop` | Drop files or MIME data onto an element | Simulates drag-from-OS. Pass file paths or MIME data. The only way to test drop zones that do NOT use a hidden `<input type="file">`. |

### 1.5 File I/O (1 tool)

| Tool | Purpose | Notable Behavior |
|------|---------|------------------|
| `mcp__playwright__browser_file_upload` | Hand files to a triggered file chooser | Must be called AFTER the action that opens the chooser (clicking an Upload button). Pass `paths: []` (empty array) to cancel the chooser. The chooser event is single-shot; if you miss it, you must re-trigger. |

### 1.6 Dialog Handling (1 tool)

| Tool | Purpose | Notable Behavior |
|------|---------|------------------|
| `mcp__playwright__browser_handle_dialog` | Accept or dismiss a native `alert`/`confirm`/`prompt` | Required when JS calls `alert()`, `confirm()`, or `prompt()` — without this, the page stalls. `accept: true` clicks OK; for `prompt`, supply `promptText`. |

### 1.7 Script Execution — Escape Hatches (2 tools)

| Tool | Purpose | Notable Behavior |
|------|---------|------------------|
| `mcp__playwright__browser_evaluate` | Run a JS expression on the page or on one element | Sandboxed to a single expression. Can target an element via ref. Returns serializable result. Use for: extracting computed styles, reading DOM attributes the snapshot omits, calling page-level helpers. |
| `mcp__playwright__browser_run_code_unsafe` | Full Playwright `page` access | Equivalent to RCE: arbitrary Playwright API including `page.context()`, `page.waitForEvent()`, request interception, cookie jar access. This is the ONLY way to capture downloads, read/write cookies, intercept network at the protocol level, or use any Playwright API not exposed by other MCP tools. Treat it as the master key — use sparingly and audit every call. |

---

## 2. Critical Gaps and Quirks

The MCP surface is intentionally narrow. Several common Playwright operations are absent or behave differently than the underlying Playwright API. Knowing these gaps prevents silent failure.

| Gap | Why It Matters | Workaround |
|-----|----------------|------------|
| No native "download file" tool | Meesho bulk-upload templates are XLSX downloads; we cannot harvest them with `browser_click` alone | `browser_run_code_unsafe` + `page.waitForEvent('download')` + `download.saveAs(path)` — see snippet 2 in Section 4 |
| No cookie/storage setter | Cannot pre-seed an authenticated session across runs | Either (a) log in fresh each session, or (b) extract cookies via `browser_run_code_unsafe` and reuse them in a separate `curl`/`httpx` client |
| No HAR export | Cannot record-and-replay sessions for offline analysis | Use `browser_network_requests` to enumerate, then `browser_network_request` per index — save bodies to disk manually |
| No headless toggle | MCP server runs in one mode (headed or headless); you cannot switch mid-session | Configure at MCP server startup; for visible debugging, start the server in headed mode |
| No proxy configuration | Cannot route traffic through a proxy from the MCP layer | Server-level config only; for per-request proxying use `browser_run_code_unsafe` with `page.context().request.fetch()` and a custom agent |
| `browser_snapshot` refs are turn-scoped | A ref like `[e13]` valid in turn N may not exist in turn N+1 if the DOM changed (re-render, navigation, modal close) | Always re-snapshot before any action sequence. Never cache refs across turns. |
| Screenshots cannot drive actions | Refs come only from `browser_snapshot` — screenshots are pixels, not handles | Take screenshots for evidence/debugging only. Use snapshots for any tool that needs a ref. |
| No structured download progress | Large file downloads block the tool call with no progress signal | Wrap `browser_run_code_unsafe` calls in explicit timeouts; for large files (>50MB) save to disk and monitor file size out-of-band |
| `browser_select_option` does not work on custom dropdowns | React-Select, Headless UI Combobox, Radix Select all render hidden inputs but expose no native `<select>` | Use `browser_click` to open, `browser_snapshot` to find the option, `browser_click` to pick |
| `browser_file_upload` requires an already-triggered chooser | Calling it without first clicking the upload button does nothing | Sequence: click upload button → IMMEDIATELY call `browser_file_upload` in the same turn |
| Console messages are buffered from page load | Reading console twice yields the same log lines | If you need delta logging, snapshot the message count between actions |
| Network request indices reset on navigation | After `browser_navigate`, the request index restarts from 1 | Capture indices of interest before navigating away |

---

## 3. Battle-Tested Patterns

Five patterns that, applied consistently, eliminate roughly 80% of scraper failures.

### Pattern 1 — Snapshot before every action

Refs are stale across turns. Even within a turn, any tool call that mutates the DOM (click, type, navigate, wait_for that triggers a render) invalidates the prior snapshot. Cheap rule: re-snapshot immediately before any action tool call. The cost is one extra round-trip; the saving is the entire failure mode of "ref not found."

### Pattern 2 — Fill-then-click, not type-then-press

`browser_fill_form` is atomic: all fields are populated, validation runs once, no intermediate React re-renders cascade. Compare this to three separate `browser_type` calls, each of which triggers React state updates, prop drilling, and re-renders. For login forms, search forms, or any multi-field input, prefer `browser_fill_form` followed by a single `browser_click` on Submit.

### Pattern 3 — Network interception over DOM scraping

When a page renders data from an API call, the API response is the source of truth. DOM is just a rendering. Scraping the DOM means reverse-engineering layout; intercepting the network means reading structured JSON.

Workflow:
1. `browser_navigate` to the page.
2. `browser_network_requests` with a regex filter for the likely API path (e.g., `/api/categories`).
3. Identify the index of the relevant request.
4. `browser_network_request` with that index to read the JSON body.
5. Parse JSON. Done.

This is especially valuable for Meesho's category tree, which is loaded via API and only partially rendered into the DOM (lazy expansion).

### Pattern 4 — `browser_run_code_unsafe` for anything tricky

Downloads, cookies, request interception, multi-step Playwright orchestration — none of these are reachable through the narrow MCP tools. `browser_run_code_unsafe` is the escape hatch. Treat it as a write of a small Playwright script per call: take page, do thing, return serializable result.

Audit rule: every `browser_run_code_unsafe` call should fit on one screen. If the script grows, factor it into a Python orchestration layer that issues multiple smaller `browser_run_code_unsafe` calls.

### Pattern 5 — Save to disk early

Once a file (XLSX, PDF, JSON) is on local disk, all subsequent processing is offline — no browser, no MCP, no rate limits. The expensive resource is the browser session; do not hold it open while parsing.

Workflow:
1. Browser tool: download to `/tmp/meesho_templates/{slug}.xlsx`.
2. Browser tool: navigate to next category.
3. Python (out of band): parse the XLSX with `openpyxl` or `pandas`.

Never parse XLSX inside `browser_run_code_unsafe` — that wastes browser context and gives up Python's much richer parsing ecosystem.

---

## 4. Concrete Code Snippets

All snippets are tested patterns. Use them as templates; substitute the specific selectors/refs from a fresh `browser_snapshot`.

### Snippet 1 — Login flow

The canonical fill-then-click pattern. Assume `browser_snapshot` has produced refs `e10` for email, `e11` for password, `e12` for submit.

```js
// Turn 1: navigate
browser_navigate({ url: "https://supplier.meesho.com/login" })

// Turn 2: snapshot to discover refs (do this fresh, do not cache)
browser_snapshot()

// Turn 3: fill the form atomically
browser_fill_form({
  fields: [
    { name: "email",    type: "textbox", ref: "e10", value: "supplier@example.com" },
    { name: "password", type: "textbox", ref: "e11", value: "REDACTED" }
  ]
})

// Turn 4: submit
browser_click({ element: "Login button", ref: "e12" })

// Turn 5: wait for dashboard text to appear (deterministic)
browser_wait_for({ text: "Dashboard" })
```

Note the explicit `browser_wait_for` with a text marker from the post-login page. Never use a time-based wait for navigation — text-based waits succeed as soon as the page is ready and fail fast if login was rejected.

### Snippet 2 — Capture a file download to disk

This is the canonical use of `browser_run_code_unsafe`. The MCP layer has no `browser_download` tool; this is the only path.

```js
async (page) => {
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('button:has-text("Download Template")').click(),
  ]);
  const path = `/tmp/meesho_templates/${categorySlug}.xlsx`;
  await download.saveAs(path);
  return path;
}
```

Key points:
- `Promise.all` ensures the listener is attached BEFORE the click fires the download — otherwise the event can race past.
- `download.saveAs(path)` returns when the file is fully written; safe to read the file immediately after.
- Return the path so the orchestration layer knows where to find it.
- Substitute `categorySlug` via string interpolation at the orchestration layer before sending to `browser_run_code_unsafe`.

### Snippet 3 — Extract session cookies for reuse with curl/httpx

When the browser is just a credential vending machine. Get cookies once, then hand them to a faster Python HTTP client for bulk work.

```js
async (page) => {
  return await page.context().cookies();
}
```

Returns an array of cookie objects: `{ name, value, domain, path, expires, httpOnly, secure, sameSite }`. Convert to a `Cookie:` header or a `requests.Session().cookies` jar at the Python layer.

Caveat: HttpOnly cookies are returned (Playwright sees them); standard JS `document.cookie` would not. This is one of the few cases where the `unsafe` tool is strictly more capable than anything sandboxed.

### Snippet 4 — Authenticated request via the browser session

When an endpoint returns JSON and you want to bypass DOM rendering entirely, fire the request from the browser's own context (so cookies, CSRF tokens, etc. ride along automatically).

```js
async (page) => {
  const res = await page.context().request.get('https://supplier.meesho.com/api/categories');
  return await res.json();
}
```

This uses Playwright's APIRequestContext, which shares the browser's cookie jar and TLS session. For most authenticated JSON endpoints, this is far faster than navigating + scraping the rendered DOM.

### Snippet 5 — Network response interception by URL substring

Capture a specific XHR response (e.g., the category-tree API) without polling `browser_network_requests`. Register a listener BEFORE the action that triggers the request.

```js
async (page) => {
  const responsePromise = page.waitForResponse(
    response => response.url().includes('/api/categories') && response.status() === 200,
    { timeout: 15000 }
  );
  await page.locator('a:has-text("Catalog")').click();
  const response = await responsePromise;
  return await response.json();
}
```

This pattern is essential when:
- The request fires only as a side effect of a user action.
- The response is large and you want it parsed in-memory rather than re-fetched.
- The endpoint requires headers (CSRF, auth) that the browser auto-populates.

---

## 5. Workflow Mapping for Meesho Supplier Panel Scraping

The end-to-end Meesho scraping workflow has six phases. Phases 1-4 and 6 are browser work (Playwright MCP). Phase 5 is offline Python — explicitly not a Playwright concern but listed here for completeness.

### Phase 1 — Login

**Goal**: Establish an authenticated session.

| Step | Tool | Notes |
|------|------|-------|
| 1.1 | `browser_navigate` | URL: `https://supplier.meesho.com/login` |
| 1.2 | `browser_snapshot` | Discover refs for email, password, submit |
| 1.3 | `browser_fill_form` | Email + password in one call |
| 1.4 | `browser_click` | Submit button |
| 1.5 | `browser_wait_for` | Wait for dashboard text marker (e.g., `text: "Dashboard"`) |
| 1.6 | `browser_take_screenshot` | Optional: save as login-success evidence |

If Phase 1.5 times out, treat it as a hard failure (captcha, invalid credentials, account locked). Do not retry-storm; surface to operator.

### Phase 2 — Navigate to Bulk Upload

**Goal**: Reach the Bulk Upload page where category templates are listed.

| Step | Tool | Notes |
|------|------|-------|
| 2.1 | `browser_snapshot` | Find ref for Catalog menu |
| 2.2 | `browser_hover` | Hover the Catalog menu (may be needed to reveal submenu) |
| 2.3 | `browser_snapshot` | Re-snapshot after hover; submenu items now have refs |
| 2.4 | `browser_click` | Click "Bulk Upload" or equivalent menu item |
| 2.5 | `browser_wait_for` | Wait for a marker text on the Bulk Upload page |

### Phase 3 — Enumerate categories

**Goal**: Build a list of every leaf category for which a template can be downloaded.

Two strategies — pick based on what the page exposes.

**Strategy 3A — DOM snapshot**: If categories are rendered as a tree in the DOM, walk it via `browser_snapshot`. Cheap and structured but requires expansion clicks for lazy-loaded subtrees.

| Step | Tool | Notes |
|------|------|-------|
| 3A.1 | `browser_snapshot` | Read the visible category tree |
| 3A.2 | `browser_click` | Expand a collapsed branch |
| 3A.3 | `browser_snapshot` | Re-read after expansion |
| 3A.4 | Repeat 3A.2-3A.3 until fully expanded | |

**Strategy 3B — Network interception (preferred)**: If categories come from an API, intercept the JSON directly.

| Step | Tool | Notes |
|------|------|-------|
| 3B.1 | `browser_network_requests` | Filter for `/api/categor*` or similar |
| 3B.2 | `browser_network_request` | Read the response body of the matching index |
| 3B.3 | Parse JSON in the orchestration layer | Build the leaf-category list |

Strategy 3B is almost always faster and more complete. Use 3A only if the page does not call a categories API.

### Phase 4 — Download templates per leaf category

**Goal**: For each leaf category, navigate the bulk-upload UI to trigger an XLSX download and save to disk.

| Step | Tool | Notes |
|------|------|-------|
| 4.1 | `browser_snapshot` | Locate category selector |
| 4.2 | `browser_click` | Click through to leaf (may take multiple clicks for nested categories) |
| 4.3 | `browser_wait_for` | Wait for the download button to appear |
| 4.4 | `browser_run_code_unsafe` | Execute Snippet 2 (download capture) with the leaf slug |
| 4.5 | `browser_wait_for` | Throttle: `time: 2-5` seconds, jittered |
| 4.6 | Loop to 4.1 for next category | |

Throttling is non-negotiable — see Section 6.

### Phase 5 — Parse XLSX (offline Python, not Playwright)

**Goal**: Convert downloaded XLSX templates into structured records (field name, data type, required flag, validation rules, dropdown values).

| Step | Tool | Notes |
|------|------|-------|
| 5.1 | `openpyxl` or `pandas` | Read each XLSX from `/tmp/meesho_templates/` |
| 5.2 | Python | Extract sheet structure, named ranges, data validations |
| 5.3 | Python | Normalize into JSON schema per category |
| 5.4 | Python | Write consolidated schema to `data/meesho_categories.json` (or equivalent) |

This phase is outside Playwright MCP scope. Listed for workflow completeness; do not invoke browser tools here.

### Phase 6 — Cross-validate against single-upload UI

**Goal**: Sanity-check the parsed XLSX schema by comparing against the live single-upload form UI for a sampled category.

| Step | Tool | Notes |
|------|------|-------|
| 6.1 | `browser_navigate` | Single-upload route for the sampled category |
| 6.2 | `browser_snapshot` | Capture form structure |
| 6.3 | `browser_evaluate` or `browser_snapshot` | Extract field labels, required markers, dropdown options |
| 6.4 | Compare to parsed XLSX schema | Flag mismatches for manual review |

If the UI shows fields that the XLSX does not (or vice versa), the XLSX template parser needs a fix or the UI uses additional fields not exposed via bulk upload — log the delta and surface.

---

## 6. Security and Responsible Use

Browser automation against a third-party platform carries operational and legal risk. The rules below are non-negotiable for this project.

### 6.1 Scope of access

- Operate only against accounts the user (operator) owns or has explicit authorization to access.
- This is for the operator's own Meesho supplier panel — not for scraping competitors, harvesting other sellers' data, or any cross-account activity.
- Do not collect PII of buyers, other sellers, or platform staff. The Meesho supplier panel does expose buyer addresses on orders — these are out of scope.

### 6.2 Platform policy

- Read and honor `robots.txt` for `supplier.meesho.com`.
- Comply with Meesho supplier Terms of Service. Where the ToS forbids automated access, escalate to the operator before proceeding — do not silently continue.
- Identify the automation if possible (custom User-Agent) so platform support can correlate logs if there is a question.

### 6.3 Throttling and politeness

- Insert jittered delays between actions: 2-5 seconds between category downloads, 1-2 seconds between intra-page clicks.
- Never parallelize requests against the same account from multiple browser sessions. One session, sequential, slow.
- Cap total runs per day. A nightly category-enumeration pass is fine; hourly is abusive.

### 6.4 Hard stops

If any of the following occur, halt the scraper immediately and surface to the operator. Do not retry, do not back off and continue:

- HTTP `403 Forbidden` response on a request that previously worked.
- HTTP `429 Too Many Requests`.
- A captcha challenge appears on screen (detect via known captcha provider snippets or via `browser_console_messages`).
- A "Your account has been suspended" or similar warning page renders.
- Login fails twice in a row.

Retry-storming any of these escalates the issue. A human must reset.

### 6.5 Credential handling

- Never log passwords, session cookies, or authorization headers — not in console output, not in saved network requests, not in error reports.
- Credentials live in environment variables or a secret manager (e.g., GCP Secret Manager). Never in source, never in `.nexus/` artifacts, never in commit history.
- When extracting cookies for reuse (Snippet 3), store them in memory or in a chmod-600 file under `/tmp/`. Wipe on session end.
- If a snapshot, screenshot, or network capture contains a credential by accident, delete the artifact immediately and revoke the credential.

### 6.6 Audit trail

- Every scraper run writes a structured log: timestamp, account, phase, action, outcome. No credentials in the log.
- Downloaded files include a sidecar `.meta.json` with: source URL, download timestamp, category slug, response headers (sanitized).
- Logs and metadata are retained for 30 days for debugging, then purged.

---

## Appendix A — Quick Tool Lookup

| If you need to... | Use this tool |
|-------------------|---------------|
| Go to a URL | `browser_navigate` |
| Find element IDs to act on | `browser_snapshot` |
| Click a button or link | `browser_click` |
| Fill a multi-field form | `browser_fill_form` |
| Pick a value from a native `<select>` | `browser_select_option` |
| Pick a value from a custom dropdown | `browser_click` (open) + `browser_click` (option) |
| Wait for the page to be ready | `browser_wait_for` with `text:` |
| Sleep N seconds | `browser_wait_for` with `time:` |
| Capture evidence | `browser_take_screenshot` |
| Read the API the page is calling | `browser_network_requests` + `browser_network_request` |
| Download a file | `browser_run_code_unsafe` (Snippet 2) |
| Get session cookies | `browser_run_code_unsafe` (Snippet 3) |
| Call an authenticated JSON endpoint | `browser_run_code_unsafe` (Snippet 4) |
| Open a new tab | `browser_tabs` with `new` |
| Switch tabs | `browser_tabs` with `select` |
| Handle a JS `alert()` | `browser_handle_dialog` |
| Upload a file | click the upload button, then `browser_file_upload` |
| Drag-and-drop from OS | `browser_drop` with file paths |
| Read JS console errors | `browser_console_messages` |
| Anything not listed above | `browser_run_code_unsafe` |

---

## Appendix B — Document Maintenance

- This document is the contract for browser automation in `mesell`. If you discover a behavior here that no longer matches the MCP server's behavior, update this document in the SAME commit as the code that depends on the new behavior.
- When new Playwright MCP tools are exposed (server upgrade), add them to Section 1 in the correct category, document quirks in Section 2, and add usage patterns to Section 3 if non-obvious.
- The Meesho workflow in Section 5 is the canonical reference. If the workflow changes (new pages, new auth flow, new template format), update Section 5 before changing scraper code.
