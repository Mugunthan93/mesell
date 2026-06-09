# WAVE 1A FOLLOWUP — Q1 SIDEBAR FOOTER LOGOUT REMOVAL — MICRO-DISPATCH

| Field | Value |
|---|---|
| **Document type** | Micro-dispatch notification (master → sub-session) |
| **Wave** | 1A Followup — Q1 micro-fix |
| **Type** | Standalone micro-dispatch (NOT bundled with Wave 1C) |
| **Date authored** | 2026-06-08 |
| **Status** | 📤 READY TO DISPATCH (awaiting founder paste into cross-cutting session) |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | mesell-ui-base-2 (cross-cutting session) |
| **Predecessor** | `WAVE_1A_AREA_1_LAYOUTS_DISPATCH.md` §14.4 Q1 ruling |
| **Parallel work** | `WAVE_1B_TEMPLATE_RESEARCH_DISPATCH.md` (mesell-design-system-2) — runs in parallel; this dispatch does not block or depend on it |
| **Estimated scope** | ~5-15 lines deleted in shell.component.ts; possibly 1 test removed |

---

## 1. Purpose

Cross-cutting's STATUS update 2026-06-08 surfaced an open question:

> Sidebar footer still has a "Logout" text button (pre-existing). Both sidebar logout + header dropdown "Log out" now route to /login. If founder wants sidebar footer logout REMOVED (cleaner header-only pattern like Spike), flag for Wave 1B or a separate micro-dispatch.

**Founder ruling 2026-06-08**: ✅ **REMOVE** the sidebar footer logout. **Send as standalone micro-dispatch now** (not bundled into Wave 1C).

**Why standalone now**:
- Duplicate logout creates UX ambiguity (two buttons, same action)
- Wave 1B research window may take days — sitting tech debt
- Wave 1A header dropdown "Log out" is sufficient and tested (5/5 new tests pass)
- Fix is small + isolated — no Wave 1B dependency, no Wave 1C dependency

---

## 2. Scope

### 2.1 Files in scope

| File | Action |
|---|---|
| `frontend/src/app/layouts/shell/shell.component.ts` | Remove sidebar footer Logout button (template + any controller wiring specific to the sidebar footer logout) |
| `frontend/src/app/layouts/shell/shell.component.spec.ts` | Remove/update any test that asserts sidebar-footer-logout presence; preserve all header-dropdown logout tests |

### 2.2 Files explicitly NOT in scope

| File | Why |
|---|---|
| `frontend/src/app/layouts/auth/auth-layout.component.ts` | No sidebar; not affected |
| `frontend/src/app/core/services/auth.service.ts` | `AuthService.logout()` continues unchanged — header dropdown still uses it |
| Any other `frontend/src/` file | Out of scope for this micro-dispatch |
| `_tokens.scss` | No token changes |
| `themes/<wave_1b_candidate>/` | Wave 1B parallel work — don't touch |

---

## 3. The Change (specific)

### 3.1 Expected current state (cross-cutting to verify)

In `shell.component.ts`, the sidebar footer contains a text button labeled "Logout" that calls `this.logout()` (or similar). This is pre-existing — predates the Wave 1A header dropdown.

### 3.2 Required end state

- Sidebar footer "Logout" text button **removed** from the template
- If the button was the ONLY consumer of any sidebar-footer-specific helper (e.g., a `sidebarLogout()` method that wrapped `logout()`), remove that helper too
- If `logout()` method itself is still used by the header dropdown (Wave 1A: it is), **leave `logout()` intact**
- If the sidebar footer becomes empty after removal, decide whether to:
  - (a) Remove the now-empty footer container element entirely, OR
  - (b) Leave the container in place if other footer content was planned (per founder decision, no other content planned)
  - **Default: (a)** — remove the empty container for cleaner DOM

### 3.3 Visual outcome

| Element | Before | After |
|---|---|---|
| Header avatar dropdown "Log out" | Present (Wave 1A) | Present, unchanged |
| Sidebar footer "Logout" button | Present (pre-existing) | **Removed** |
| Sidebar footer container | Present | Removed if empty after button removal |

---

## 4. Constraints (non-negotiable)

| Constraint | Rule |
|---|---|
| **AuthService.logout() preserved** | The method itself stays — header dropdown depends on it |
| **No new hex** | No styling changes — this is pure deletion |
| **No new dependencies** | Pure code removal |
| **Header dropdown logout tests preserved** | All 5 Wave 1A tests (avatar aria-label, bell absence, "My Profile" nav, "Log out" full path, direct logout call) must continue to pass |
| **OnPush + signals discipline preserved** | No regression in change-detection strategy |
| **No regression in non-logout sidebar functionality** | Nav items, branding, sections — all unchanged |
| **Dispatch only `meesell-*` agents** | Per CLAUDE.md ecosystem rules |
| **Memory hygiene** | Cross-cutting writes learnings to `.claude/agent-memory/mesell-ui-base/MEMORY.md` only |

---

## 5. Out of Scope (do not touch)

| Out-of-scope item | Reason |
|---|---|
| Other layout files | Q1 is sidebar-specific |
| `AuthService.logout()` itself | Header dropdown depends on it; only its caller changes |
| Sidebar nav items | Pre-existing, working correctly |
| Sidebar branding | Pre-existing, working correctly |
| Sidebar section headers | Pre-existing, working correctly |
| Token changes | Pure deletion, no styling |
| New components | Not needed |
| Wave 1B template research | Parallel session's work |
| API integration | Still on hold |
| Mobile / Ionic / Module Federation | Phase 2 |

---

## 6. Verification Gates

### Gate 1 — BUILD

```bash
cd frontend && ng build --configuration=production
```

**Pass criteria**: zero errors, zero new warnings, shell bundle stays within 80 KB budget.

### Gate 2 — TOKEN HYGIENE (sanity — no styling change expected)

```bash
grep -rnE "#[0-9a-fA-F]{3,6}" frontend/src/app/layouts/shell/
```

**Pass criteria**: no new hex matches (count should be same as Wave 1A post-state).

### Gate 3 — FUNCTIONAL

```bash
cd frontend && pnpm vitest run frontend/src/app/layouts/shell/
```

**Pass criteria**:
- 5 Wave 1A header-dropdown tests still pass (no regression)
- Any sidebar-footer-logout-specific test cleanly removed or updated
- Overall shell.component.spec.ts test count = (Wave 1A end-state count) - N (N being sidebar-footer-logout tests removed)

### Gate 4 — VISUAL REGRESSION (founder-side, opt-in)

```bash
cd frontend && ng serve
```

Founder visits `http://localhost:4200/dashboard` and verifies:
- Sidebar footer no longer shows "Logout" button
- Header avatar dropdown still opens and "Log out" still works (clicking logs out + routes to `/login`)

**Pass criteria**: Founder verbal approval. If skipped, mark Gate 3 as conclusive.

### 6.1 Gate tracking table

| Gate | Status | Verified by | Date | Evidence |
|---|---|---|---|---|
| 1 — BUILD | ⏳ pending | Cross-cutting | — | — |
| 2 — TOKEN | ⏳ pending | Cross-cutting | — | — |
| 3 — FUNCTIONAL | ⏳ pending | Cross-cutting | — | — |
| 4 — VISUAL REGRESSION | ⏳ pending (optional) | Founder | — | — |

---

## 7. Dispatch Notification (paste-ready block)

The following block is to be pasted **verbatim** into the cross-cutting sub-session (`mesell-ui-base-2`).

```
══════════════════════════════════════════════════════════════════
📨 MASTER → CROSS-CUTTING MICRO-DISPATCH
Date: 2026-06-08
From: meesell-frontend-coordinator (master session)
Type: Standalone micro-dispatch — Wave 1A followup Q1
Reference: WAVE_1A_AREA_1_LAYOUTS_DISPATCH.md §14.4 Q1 ruling
══════════════════════════════════════════════════════════════════

PURPOSE
───────
Wave 1A landed a header avatar dropdown with "Log out" in
shell.component.ts. The sidebar footer still has a pre-existing
"Logout" text button — duplicate action, UX ambiguity.

Founder ruling 2026-06-08: REMOVE sidebar footer Logout.
Send as standalone micro-dispatch NOW (not bundled into Wave 1C).
Wave 1B template research is parallel and unrelated — do not block.

══════════════════════════════════════════════════════════════════

SCOPE — MICRO
─────────────
Files in scope:
  • frontend/src/app/layouts/shell/shell.component.ts
    — Remove sidebar footer "Logout" text button from template
    — Remove any sidebar-footer-only helper method if it has no
      other consumer
  • frontend/src/app/layouts/shell/shell.component.spec.ts
    — Remove or update any test asserting sidebar-footer-logout
      presence
    — PRESERVE all 5 Wave 1A header-dropdown logout tests

NOT in scope (do NOT touch):
  ✗ AuthService.logout() — header dropdown depends on it
  ✗ Any other frontend/src/ file
  ✗ _tokens.scss / styling
  ✗ Other layout files (auth-layout, etc.)
  ✗ Sidebar nav items, branding, section headers (all pre-existing,
    working)
  ✗ themes/<wave_1b_candidate>/ — Wave 1B parallel work
  ✗ API integration — still on hold

══════════════════════════════════════════════════════════════════

CHANGE SPECIFICATION
────────────────────
Expected current state:
  Sidebar footer contains a text button labeled "Logout" that calls
  this.logout() (or similar). Pre-existing — predates Wave 1A.

Required end state:
  • Sidebar footer "Logout" text button REMOVED from template
  • If the button was the only consumer of any sidebar-footer-
    specific helper, remove that helper too
  • logout() method itself STAYS — header dropdown still uses it
  • If sidebar footer becomes empty, REMOVE the empty container
    element (default: clean DOM)

Visual outcome:
  Before: 2 logout actions (sidebar footer + header dropdown)
  After:  1 logout action (header dropdown only)

══════════════════════════════════════════════════════════════════

CONSTRAINTS (non-negotiable)
────────────────────────────
• AuthService.logout() PRESERVED — header dropdown depends on it
• No new hex — pure deletion, no styling change
• No new dependencies — pure code removal
• All 5 Wave 1A header-dropdown tests MUST continue to pass:
    1. Avatar aria-label="Open profile menu"
    2. Notification bell absent
    3. "My Profile" menu item → /profile
    4. "Log out" menu item → AuthService.logout() + /login
    5. Direct logout() call → AuthService.logout() + /login
• OnPush + signals discipline preserved
• No regression in sidebar nav / branding / sections
• Dispatch only meesell-* agents
• Memory hygiene: .claude/agent-memory/mesell-ui-base/MEMORY.md only

══════════════════════════════════════════════════════════════════

VERIFICATION GATES
──────────────────

Gate 1 — BUILD
  Command: cd frontend && ng build --configuration=production
  Pass criteria: zero errors, zero new warnings, shell bundle ≤80 KB

Gate 2 — TOKEN HYGIENE (sanity)
  Command: grep -rnE "#[0-9a-fA-F]{3,6}" frontend/src/app/layouts/shell/
  Pass criteria: no new hex matches (count same as Wave 1A post-state)

Gate 3 — FUNCTIONAL
  Command: cd frontend && pnpm vitest run frontend/src/app/layouts/shell/
  Pass criteria:
    • All 5 Wave 1A header-dropdown tests pass
    • Sidebar-footer-logout test(s) cleanly removed/updated
    • No new failures

Gate 4 — VISUAL REGRESSION (optional, founder-side)
  Command: cd frontend && ng serve
  Founder check:
    • Sidebar footer no longer shows "Logout" button
    • Header avatar dropdown still opens
    • "Log out" in dropdown still routes to /login

══════════════════════════════════════════════════════════════════

DISPATCH PATTERN
────────────────
You (cross-cutting session) will:
  1. Read shell.component.ts to locate sidebar footer Logout
     button + any sidebar-footer-only helper method
  2. Read shell.component.spec.ts to identify any sidebar-footer-
     logout-specific tests
  3. Dispatch meesell-angular-component-builder ONE agent with:
       • the change specification above
       • the constraints
       • the gates
  4. When agent returns, run Gates 1+2+3 yourself
  5. Append UPDATE block to STATUS_FEATURE_CROSS_CUTTING.md
  6. Notify master — master surfaces to founder for optional Gate 4

══════════════════════════════════════════════════════════════════

STATUS UPDATE BLOCK (append to STATUS_FEATURE_CROSS_CUTTING.md)
───────────────────────────────────────────────────────────────

  ═══════════════════════════════════════════════════════
  UPDATE 2026-06-08 — WAVE 1A FOLLOWUP Q1 SIDEBAR LOGOUT
  ═══════════════════════════════════════════════════════
  Trigger: founder ruling 2026-06-08 — standalone micro-dispatch
  Wave 1A header dropdown logout: unchanged + still passing
  Files modified:
    layouts/shell/shell.component.ts       (−N lines)
    layouts/shell/shell.component.spec.ts  (−M lines / updated)
  Helper methods removed: [list any]
  Empty containers removed: [yes/no]
  Tests removed/updated:   [count + description]
  Tests passing:           [N/M]
    Wave 1A 5 header-dropdown tests:   ✅ all pass
  Gate 1 BUILD:            ✅/❌ [evidence]
  Gate 2 TOKEN:            ✅/❌ [grep output]
  Gate 3 FUNCTIONAL:       ✅/❌ [test output]
  Gate 4 VISUAL:           ⏳ pending founder review (optional)
  Open questions:          [any blockers for master]

══════════════════════════════════════════════════════════════════

DECISION POINT (master, post-completion)
────────────────────────────────────────
After Gates 1+2+3 pass:
  → Master surfaces to founder for optional Gate 4 visual check
  → Wave 1A followup Q1 marked CLOSED
  → Cross-cutting session continues with whatever was queued
     before this micro-dispatch
  → Wave 1B (design-system-2) continues independently in parallel

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```

---

## 8. Workflow After Paste

| Step | Owner | Action |
|---|---|---|
| 1 | Founder | Paste §7 block into `mesell-ui-base-2` |
| 2 | Cross-cutting session | Locate sidebar footer Logout in `shell.component.ts` |
| 3 | Cross-cutting session | Identify sidebar-footer-logout-specific tests |
| 4 | Cross-cutting session | Dispatch `meesell-angular-component-builder` with change spec |
| 5 | Build agent | Remove button + helper (if isolated) + container (if empty) |
| 6 | Build agent | Update tests (remove sidebar-footer-logout assertions; preserve Wave 1A 5) |
| 7 | Cross-cutting session | Run Gates 1+2+3 |
| 8 | Cross-cutting session | Append UPDATE block to `STATUS_FEATURE_CROSS_CUTTING.md` |
| 9 | Cross-cutting → Master | Notify completion |
| 10 | Master → Founder | Surface + offer optional Gate 4 visual check |
| 11 | Founder | (Optional) Verify visually via `ng serve` |
| 12 | Master | Mark Wave 1A Followup Q1 CLOSED |

---

## 9. Relationship to Other Waves

| Wave | Status | Relationship |
|---|---|---|
| **Wave 1A Area 1 (Layouts)** | 🏁 CLOSED with addendum | Predecessor — Q1 originated as open question in Wave 1A STATUS update |
| **Wave 1A Followup Q1 (this dispatch)** | 📤 READY | Current — standalone micro-fix per founder elevation |
| **Wave 1B (Template Research)** | 📤 READY (separate dispatch) | Parallel — runs in `mesell-design-system-2`, unrelated, non-blocking |
| **Wave 1C (Template Implementation)** | 🔒 PENDING | Future — depends on Wave 1B ratification; will land in `mesell-ui-base-2` after Wave 1B closes |

**Key**: Wave 1A Followup Q1 and Wave 1B are **fully parallel**. Cross-cutting session can execute this micro-dispatch even while design-system-2 is mid-research. No coordination needed between the two sessions for this work.

---

## 10. Related Documents

| Document | Relevance |
|---|---|
| `docs/ui_ux/WAVE_1A_AREA_1_LAYOUTS_DISPATCH.md` §14.4 | Q1 ruling origin |
| `docs/ui_ux/WAVE_1B_TEMPLATE_RESEARCH_DISPATCH.md` | Parallel work — not a dependency |
| `docs/status/STATUS_FEATURE_CROSS_CUTTING.md` | Receives UPDATE block post-completion |
| `frontend/src/app/layouts/shell/shell.component.ts` | Primary file to modify |
| `frontend/src/app/layouts/shell/shell.component.spec.ts` | Test file to update |
| `frontend/src/app/core/services/auth.service.ts` | Untouched but referenced — `logout()` continues working |

---

## 11. Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-08 | meesell-frontend-coordinator (master) | Initial authoring after founder elevated Q1 from "bundle into Wave 1C" to "standalone now" |
