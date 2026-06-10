# WAVE 5 — EXPORT — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Feature: Export (F12) |
| **Date authored** | 2026-06-09 |
| **Status** | READY |
| **Agent** | `meesell-angular-component-builder` |
| **Recipient** | Sub-session executing Wave 5 group C |
| **Depends on** | Wave 3 UI Kit complete (ui/index.ts stable) + Wave 4 Composites complete |

---

## 1. Module Summary

| Property | Value |
|---|---|
| **Route** | `/catalogs/:id/export` |
| **Component class** | `ExportComponent` |
| **Selector** | `app-export` |
| **Location** | `src/app/features/export/export/export.component.ts` |
| **Shell relationship** | Child of `MeeShellComponent` (rendered via shell router-outlet) |
| **Purpose** | Validates all compulsory fields are complete and at least 1 image has passed pre-check; triggers async XLSX + image ZIP generation; polls status; shows download URL when ready. |
| **Status** | NOT BUILT |

---

## 2. Dependencies

### UI Kit primitives (Layer 2 — mee-* only)
| Primitive | Usage |
|---|---|
| `mee-button` | "Generate Export" trigger; "Download XLSX" anchor; "Retry" on failure |
| `mee-progress-bar` | Generation progress (simulated 0→100 over ~5 s) |
| `mee-badge` | Per-validation-check pass/fail status chips |
| `mee-card` | Validation summary card; export progress card; download card |

### Composites (Layer 3)
| Composite | Usage |
|---|---|
| `mee-page-header` | Page title "Export Catalog" + subtitle |
| `mee-status-badge` | Overall export job status (processing / ready / failed) |

### Layout
- Shell child — no layout component import needed.

### API endpoints (V1_FEATURE_SPEC §5)
| Method | Path | Used for |
|---|---|---|
| `POST` | `/api/v1/products/{id}/export-xlsx` | Trigger XLSX + ZIP generation; returns `{ export_id }` |
| `GET` | `/api/v1/exports/{id}` | Poll export job status + download URL |

> **SIMULATE strategy:**
> 1. On "Generate Export" click: set `exportStatus.set('processing')`, start `progress` signal at 0.
> 2. Use `setInterval` every 500 ms to increment `progress` signal by ~10 each tick.
> 3. At progress ≥ 100 (after ~5 s): set `exportStatus.set('ready')`, clear interval, set `downloadUrl.set('https://storage.example.com/exports/mock-kurti.xlsx')`.
> 4. Simulate validation: all checks pass (journey step 10 — validation passes before generating).
> No HttpClient wiring.

> ⚠️ BOUNDARY: import ONLY from `../../ui`, `../../shared`, `../../layouts`, own services. ZERO `primeng/...` imports.

---

## 3. Files to Create / Modify

| Action | Path |
|---|---|
| Create | `src/app/features/export/export/export.component.ts` |
| Create | `src/app/features/export/export/export.component.spec.ts` |
| Create | `src/app/features/export/export/export.model.ts` |
| Update | `docs/status/STATUS_FRONTEND.md` |

Do NOT modify `app.routes.ts` — route registration is coordinator scope.

---

## 4. Component Spec

### ASCII layout — 360px mobile first

```
┌─────────────────────────────────────┐
│  mee-page-header                    │
│  "Export Catalog"                   │
│  "Generate Meesho-format XLSX"      │
├─────────────────────────────────────┤
│  VALIDATION GATE (mee-card)         │
│  ┌─────────────────────────────┐    │
│  │  Pre-export checklist       │    │
│  │                             │    │
│  │  Check               Result │    │
│  │  Title filled        PASS   │    │  ← mee-badge severity=success
│  │  Category selected   PASS   │    │
│  │  Compulsory fields   PASS   │    │
│  │  ≥1 image (pass)     PASS   │    │
│  │                             │    │
│  │  All checks passed.         │    │
│  │  Ready to generate export.  │    │
│  └─────────────────────────────┘    │
│                                     │
│  [Generate Export]  mee-button      │
│  (primary, full-width)              │
│  (disabled if any validation fails) │
├─────────────────────────────────────┤
│  PROGRESS CARD (mee-card)           │
│  (visible only when status ≠ idle)  │
│  ┌─────────────────────────────┐    │
│  │  mee-status-badge           │    │
│  │  "PROCESSING" / "READY"     │    │
│  │  / "FAILED"                 │    │
│  │                             │    │
│  │  mee-progress-bar           │    │
│  │  ████████░░░░░░ 72%         │    │  ← animated 0→100
│  │                             │    │
│  │  Generating XLSX + images…  │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  DOWNLOAD CARD (mee-card)           │
│  (visible only when status="ready") │
│  ┌─────────────────────────────┐    │
│  │  Your export is ready!      │    │
│  │                             │    │
│  │  [Download XLSX]            │    │  ← mee-button + native <a> href
│  │  (secondary, full-width)    │    │
│  │                             │    │
│  │  Link expires in 1 hour.    │    │
│  │                             │    │
│  │  [Back to Dashboard]        │    │  ← mee-button ghost
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  ERROR CARD (mee-card)              │
│  (visible only when status="failed")│
│  ┌─────────────────────────────┐    │
│  │  Export failed.             │    │
│  │  Please try again.          │    │
│  │  [Retry]  mee-button        │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

Desktop (1280px): Validation card (left, 40%) + Progress/Download/Error card (right, 60%) in 2-column layout. Progress and Download cards toggle (not stacked).

### Validation gate checks (4 items, simulated — all pass)
| Check | Property | Simulated result |
|---|---|---|
| Title filled | `validation.title_ok` | `true` |
| Category selected | `validation.category_ok` | `true` |
| Compulsory fields complete | `validation.fields_ok` | `true` |
| At least 1 image (pre-check pass) | `validation.images_ok` | `true` |

Simulated as all-pass to match journey step 10. To test failure state: add a hidden toggle or spec test that sets one check to false — the "Generate Export" button disables and the badge shows "FAIL" (danger severity).

### Async poll pattern (simulated with setInterval)
```
State machine:
  idle → (click Generate) → processing → (interval ticks 0→100) → ready
                                       → (simulate failure) → failed

Transitions:
  idle:       Show validation card + Generate button
  processing: Show progress card (progress bar animating)
  ready:      Show download card (progress card hidden)
  failed:     Show error card + Retry button
```

### Signals / state
```
exportStatus = signal<'idle' | 'processing' | 'ready' | 'failed'>('idle')
progress = signal<number>(0)
downloadUrl = signal<string | null>(null)
exportId = signal<string | null>(null)
pollingIntervalId = signal<ReturnType<typeof setInterval> | null>(null)
validationChecks = signal<ValidationChecks>(SIMULATED_PASSING_CHECKS)
canGenerate = computed(() =>
  exportStatus() === 'idle' &&
  validationChecks().title_ok &&
  validationChecks().category_ok &&
  validationChecks().fields_ok &&
  validationChecks().images_ok
)
```

### Behaviors
- `ngOnInit()`: load simulated validation checks (synchronous set from constant).
- `onGenerate()`: set `exportStatus('processing')`, `progress.set(0)`, start `setInterval(() => { progress.update(p => p + 10); if (progress() >= 100) { clearInterval(...); exportStatus.set('ready'); downloadUrl.set('https://...'); } }, 500)`. Store interval ID in `pollingIntervalId`.
- `ngOnDestroy()`: `clearInterval(pollingIntervalId())` to prevent leaks.
- `onRetry()`: set `exportStatus('idle')`, `progress.set(0)`, `downloadUrl.set(null)`.
- `onDownload()`: programmatic anchor click or `window.open(downloadUrl())`.
- `onBackToDashboard()`: `router.navigate(['/dashboard'])`.

---

## 5. UI Kit Usage Map

| UI element | mee-* component | Key inputs/outputs |
|---|---|---|
| Validation per-check | `mee-badge` | `[value]="check.label"`, `[severity]="check.ok ? 'success' : 'danger'"` |
| Generate button | `mee-button` | `label="Generate Export"`, `[disabled]="!canGenerate()"`, `[loading]="exportStatus() === 'processing'"`, `(clicked)` |
| Progress bar | `mee-progress-bar` | `[value]="progress()"`, `[label]="'Generating…'"`, `[show_value]="true"` |
| Export status | `mee-status-badge` | `[status]="exportStatus()"` |
| Download button | `mee-button` | `label="Download XLSX"`, `variant="secondary"`, `[fullWidth]="true"`, `(clicked)` |
| Retry button | `mee-button` | `label="Retry"`, `variant="danger"`, `(clicked)="onRetry()"` |
| Back to dashboard | `mee-button` | `label="Back to Dashboard"`, `variant="ghost"`, `(clicked)` |
| Validation card | `mee-card` | content projection of checklist table |
| Progress card | `mee-card` | content projection of status-badge + progress-bar |
| Download card | `mee-card` | content projection of download CTA |
| Page header | `mee-page-header` | `title="Export Catalog"`, `subtitle="Generate Meesho-format XLSX"` |

---

## 6. API / Data

### Feature-local model (`export.model.ts`)
```
ValidationChecks {
  title_ok: boolean
  category_ok: boolean
  fields_ok: boolean
  images_ok: boolean
}

ExportJob {
  id: string
  status: 'processing' | 'ready' | 'failed'
  progress_pct: number
  download_url: string | null
  created_at: string
}

ExportTriggerResponse {
  export_id: string
}
```

### Simulated validation (all pass — journey step 10)
```
SIMULATED_PASSING_CHECKS: ValidationChecks = {
  title_ok: true,
  category_ok: true,
  fields_ok: true,
  images_ok: true,
}
```

### Simulated export job completion
```
After ~5 s of setInterval:
  progress: 100
  status: 'ready'
  download_url: 'https://storage.googleapis.com/mee-exports/mock-kurti-catalog.xlsx'
```

---

## 7. Constraints

- `standalone: true`, `changeDetection: ChangeDetectionStrategy.OnPush`
- Use `inject()` for all DI (ActivatedRoute, Router)
- `signal()` for all local state; `computed()` for `canGenerate`
- NO Reactive Forms on this page (no form inputs — pure trigger + poll flow)
- `ngOnDestroy()` MUST call `clearInterval(pollingIntervalId())` to prevent memory leak
- Do NOT use `takeUntilDestroyed()` with native `setInterval` — use `ngOnDestroy` guard pattern
- Download: use `window.open(url, '_blank')` or a hidden `<a [href]="downloadUrl()" download>` triggered programmatically — do NOT call any Angular Router for external URLs
- State machine transitions are strictly one-way (idle → processing → ready|failed). Retry resets to idle.
- `mee-status-badge` maps 'processing' → info, 'ready' → success, 'failed' → danger
- Design tokens only — no hex literals
- All interactive controls have `min-height: 44px`
- ZERO `primeng/...` imports

---

## 8. Out of Scope

| Item | Deferred to |
|---|---|
| Real POST /export-xlsx API call | Wave 6 API wiring |
| Real GET /exports/:id polling loop | Wave 6 (replace setInterval with interval(2000) + switchMap + takeUntil) |
| Server-sent events / WebSocket for live progress | V1.5 |
| Email notification when export ready | V1.5 |
| Bulk export (multiple products) | V1.5 |
| Export history / past downloads list | V1.5 |

---

## 9. Verification Gates

| Gate | Check | Pass condition |
|---|---|---|
| 1 BUILD | `cd frontend && pnpm run build` | Zero errors, zero new warnings |
| 2 ROUTE | Navigate to `/catalogs/test-id/export` | ExportComponent renders in shell |
| 3 VALIDATION | Page loads | All 4 checks show PASS badges; Generate button enabled |
| 4 GENERATE | Click "Generate Export" | Progress bar animates 0→100 over ~5 s; status badge shows PROCESSING → READY |
| 5 DOWNLOAD | After READY | Download card appears with download URL; Download button visible |
| 6 TESTS | `pnpm run test` | Min 5 tests pass (renders, canGenerate when all pass, Generate triggers processing state, progress reaches 100 → ready, Retry resets to idle) |
| 7 VISUAL | Review at 360px + 1280px | 360: stacked cards; 1280: 2-col layout |

---

## 10. Paste-Ready Dispatch Block

```
════════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER DISPATCH
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — F12 EXPORT (/catalogs/:id/export)
Agent: meesell-angular-component-builder
════════════════════════════════════════════════════════════════════

CONTEXT
───────
Waves 3+4 complete. This dispatch builds the Export feature page (F12).
Simulate async XLSX generation with setInterval (no HttpClient wiring).
Journey step 10: validation passes, XLSX + ZIP generated, download URL displayed.

ROUTE: /catalogs/:id/export (shell child)
COMPONENT: ExportComponent

════════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  src/app/features/export/export/export.component.ts
  src/app/features/export/export/export.component.spec.ts
  src/app/features/export/export/export.model.ts

════════════════════════════════════════════════════════════════════

UI KIT USAGE
────────────
  mee-button        → Generate (primary), Download (secondary), Retry (danger), Back (ghost)
  mee-progress-bar  → [value]="progress()" — animated 0→100 during generation
  mee-badge         → per-validation-check pass/fail (4 checks)
  mee-card          → validation card, progress card, download card, error card
  mee-page-header   → title + subtitle
  mee-status-badge  → overall export job status (processing/ready/failed)

════════════════════════════════════════════════════════════════════

ASYNC POLL PATTERN (simulated)
────────────────────────────────
State machine: idle → processing → ready | failed

onGenerate():
  exportStatus.set('processing')
  progress.set(0)
  pollingIntervalId = setInterval(() => {
    progress.update(p => p + 10)
    if (progress() >= 100) {
      clearInterval(id)
      exportStatus.set('ready')
      downloadUrl.set('https://...')
    }
  }, 500)

ngOnDestroy():
  clearInterval(pollingIntervalId())  // MANDATORY — prevent leak

onRetry():
  exportStatus.set('idle'), progress.set(0), downloadUrl.set(null)

════════════════════════════════════════════════════════════════════

VALIDATION GATE (4 checks — all simulated PASS)
────────────────────────────────────────────────
  1. Title filled        → title_ok: true
  2. Category selected   → category_ok: true
  3. Compulsory fields   → fields_ok: true
  4. ≥1 image (pass)     → images_ok: true

canGenerate = computed(() => all checks true && status === 'idle')

════════════════════════════════════════════════════════════════════

SIGNALS
───────
  exportStatus = signal<'idle'|'processing'|'ready'|'failed'>('idle')
  progress = signal<number>(0)
  downloadUrl = signal<string | null>(null)
  exportId = signal<string | null>(null)
  validationChecks = signal<ValidationChecks>(SIMULATED_PASSING_CHECKS)
  canGenerate = computed(...)

════════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────
  • standalone + OnPush + signals + inject()
  • NO Reactive Forms
  • ZERO primeng/... imports
  • ngOnDestroy MUST clearInterval
  • Design tokens only (no hex literals)
  • 44px touch targets on all interactive controls
  • Download: window.open(url, '_blank') or hidden <a> — not Router.navigate

════════════════════════════════════════════════════════════════════

VERIFICATION GATES
──────────────────
  Gate 1 BUILD:    pnpm run build → zero errors
  Gate 2 ROUTE:    /catalogs/:id/export renders in shell
  Gate 3 VALID:    4 PASS badges visible; Generate button enabled
  Gate 4 GENERATE: progress 0→100 over ~5s → status READY → download card
  Gate 5 DOWNLOAD: Download button present with mock URL
  Gate 6 TESTS:    ≥5 tests pass
  Gate 7 VISUAL:   360px stacked; 1280px 2-col

════════════════════════════════════════════════════════════════════
END DISPATCH
════════════════════════════════════════════════════════════════════
```
