# WAVE 5 — IMAGES — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Feature: Images (F9) |
| **Date authored** | 2026-06-09 |
| **Status** | READY |
| **Agent** | `meesell-angular-component-builder` |
| **Recipient** | Sub-session executing Wave 5 group C |
| **Depends on** | Wave 3 UI Kit complete (ui/index.ts stable) + Wave 4 Composites complete |

---

## 1. Module Summary

| Property | Value |
|---|---|
| **Route** | `/catalogs/:id/images` |
| **Component class** | `ImageUploaderComponent` |
| **Selector** | `app-image-uploader` |
| **Location** | `src/app/features/images/image-uploader/image-uploader.component.ts` |
| **Shell relationship** | Child of `MeeShellComponent` (rendered via shell router-outlet) |
| **Purpose** | Drag-and-drop upload of up to 6 product images; runs 5 per-image pre-checks; shows per-check pass/fail report with fix hints |
| **Status** | NOT BUILT |

---

## 2. Dependencies

### UI Kit primitives (Layer 2 — mee-* only)
| Primitive | Usage |
|---|---|
| `mee-file-upload` | Drag-drop zone; `accept="image/*"`, `[multiple]="true"`, `[max_size_mb]="5"` |
| `mee-progress-bar` | Per-image pre-check progress (0–100 as checks complete) |
| `mee-badge` | Per-check pass/fail indicator (`severity="success"` or `"danger"`) |
| `mee-card` | Image tile card wrapper for each uploaded slot |
| `mee-button` | "Re-upload" action per failed image slot; "Continue to Preview" CTA |

### Composites (Layer 3)
| Composite | Usage |
|---|---|
| `mee-page-header` | Page title "Product Images" + subtitle |
| `mee-status-badge` | Overall image status (pending / pass / fail) |
| `mee-loading-skeleton` | Skeleton tiles while polling |

### Layout
- Shell child — no layout component import needed; shell provides the frame.

### API endpoints (V1_FEATURE_SPEC §5)
| Method | Path | Used for |
|---|---|---|
| `POST` | `/api/v1/products/{id}/images` | Upload image (multipart) |
| `GET` | `/api/v1/products/{id}/images` | Poll pre-check results |

> **SIMULATE strategy:** On upload, push a synthetic `ProductImage` with `status: 'pending'` into the local signal array. After a 2s delay, resolve 3 of 4 slots as `pass` and simulate image #2 (slot index 1) as `fail` on the `color_space` check (CMYK failure — matches §3 journey step 7). Poll simulation uses `setInterval` every 1.5 s checking if any slot is still `pending`.

> ⚠️ BOUNDARY: import ONLY from `../../ui`, `../../shared`, `../../layouts`, own services. ZERO `primeng/...` imports.

---

## 3. Files to Create / Modify

| Action | Path |
|---|---|
| Create | `src/app/features/images/image-uploader/image-uploader.component.ts` |
| Create | `src/app/features/images/image-uploader/image-uploader.component.spec.ts` |
| Create | `src/app/features/images/image-uploader/image-uploader.model.ts` |
| Update | `docs/status/STATUS_FRONTEND.md` |

Do NOT modify `app.routes.ts` — route registration is coordinator scope.

---

## 4. Component Spec

### ASCII layout — 360px mobile first

```
┌─────────────────────────────────────┐
│  mee-page-header                    │
│  "Product Images"                   │
│  "Upload up to 6 images"            │
├─────────────────────────────────────┤
│  mee-file-upload (drag-drop zone)   │
│  ┌─────────────────────────────┐    │
│  │  Drop images here or        │    │
│  │  click to select            │    │
│  │  JPEG · max 5 MB each       │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  IMAGE TILES (grid 2-col → 3-col)   │
│  ┌───────────┐  ┌───────────┐       │
│  │ mee-card  │  │ mee-card  │       │
│  │ [img]     │  │ [img]     │       │
│  │ slot 0    │  │ slot 1    │       │
│  │ PASS ✓    │  │ FAIL ✗    │       │
│  │ mee-badge │  │ mee-badge │       │
│  │ progress  │  │ progress  │       │
│  └───────────┘  └───────────┘       │
│                                     │
│  PER-IMAGE PRECHECK REPORT (slot 1):│
│  ┌─────────────────────────────┐    │
│  │ Check          Result  Hint │    │
│  │ JPEG format    PASS         │    │
│  │ RGB color      FAIL  ← hint │    │  ← CMYK fail
│  │ Min resolution PASS         │    │
│  │ White BG       PASS         │    │
│  │ No watermark   PASS         │    │
│  │ [Re-upload]  mee-button     │    │
│  └─────────────────────────────┘    │
│                                     │
│  [Continue to Preview]  mee-button  │
│  (disabled if any slot is FAIL)     │
└─────────────────────────────────────┘
```

Desktop (1280px): tiles in 3-column grid; precheck report expands inline below the tile row.

### Signals / state
```
images = signal<ProductImage[]>([])         // array of up to 6 slots
uploading = signal<boolean>(false)          // global upload in-flight flag
pollingActive = signal<boolean>(false)      // true while any slot is 'pending'
expandedSlot = signal<number | null>(null)  // which tile shows full precheck table
```

### Behaviors
- `onFilesSelected(event: MeeFileUploadEvent)`: validate count <= 6, add to `images` signal with `status: 'pending'`, trigger simulated upload then poll.
- `startSimulatedPoll()`: `setInterval` every 1500 ms; for each `pending` slot, after 2 s mark as `pass` or `fail` per simulation script; clear interval when no `pending` remain.
- `onReupload(slotIndex: number)`: set slot back to `pending`, re-trigger simulation for that slot only.
- `canContinue = computed(() => images().length > 0 && images().every(img => img.status === 'pass'))`.
- `onContinue()`: `router.navigate(['/catalogs', productId, 'preview'])`.
- `expandSlot(index: number)`: toggle `expandedSlot` to show/hide precheck table.

---

## 5. UI Kit Usage Map

| UI element | mee-* component | Key inputs/outputs |
|---|---|---|
| Drop zone | `mee-file-upload` | `accept="image/*"`, `[multiple]="true"`, `[max_size_mb]="5"`, `(files_selected)` |
| Per-check result | `mee-badge` | `[value]="check.label"`, `[severity]="check.pass ? 'success' : 'danger'"` |
| Pre-check progress | `mee-progress-bar` | `[value]="slotProgress(slot)"` (0 while pending, 100 when resolved) |
| Image tile | `mee-card` | content projection: `<img>` + badges + button |
| Re-upload button | `mee-button` | `variant="secondary"`, `size="sm"`, `(clicked)` |
| Continue CTA | `mee-button` | `label="Continue to Preview"`, `[disabled]="!canContinue()"`, `variant="primary"` |
| Page header | `mee-page-header` | `title="Product Images"`, `subtitle="Upload up to 6 images"` |
| Slot status | `mee-status-badge` | `[status]="slot.status"` |
| Loading tiles | `mee-loading-skeleton` | `variant="card"` while polling |

---

## 6. API / Data

### Feature-local model (`image-uploader.model.ts`)
```
ProductImage {
  id: string
  slot_index: number          // 0-based, max 5
  gcs_url: string | null
  status: 'pending' | 'pass' | 'fail'
  precheck: PrecheckResult | null
}

PrecheckResult {
  jpeg_format: boolean
  color_space_rgb: boolean    // false = CMYK detected
  min_resolution: boolean     // ≥1500×1500 px
  white_bg: boolean
  no_watermark: boolean
}
```

### Fix hints map (static, feature-local)
```
color_space_rgb: false  → "Convert image to RGB mode before uploading (CMYK detected)"
jpeg_format: false      → "Save the image as JPEG (.jpg) before uploading"
min_resolution: false   → "Image must be at least 1500×1500 pixels"
white_bg: false         → "Use a plain white background for best results"
no_watermark: false     → "Remove watermarks or logos before uploading"
```

### Simulation script (journey step 7)
- Slot 0: all 5 checks pass after 2 s
- Slot 1: `color_space_rgb: false` (CMYK fail) — shows CMYK fix hint
- Slot 2: all pass after 2.5 s
- Slot 3: all pass after 1.8 s
- Slots 4–5: empty (not uploaded)

---

## 7. Constraints

- `standalone: true`, `changeDetection: ChangeDetectionStrategy.OnPush`
- Use `inject()` for all DI (ActivatedRoute, Router, DestroyRef)
- `signal()` for all local state; `computed()` for `canContinue` and `slotProgress`
- NO Reactive Forms (no form fields — file upload is event-driven)
- Use `takeUntilDestroyed(destroyRef)` if wrapping `setInterval` in an RxJS `interval()` Observable
- Clear polling interval in `ngOnDestroy` if using native `setInterval`
- ALL interactive controls have `min-height: 44px` (mee-button enforces; tile click area must be >= 44px)
- Design tokens only: `var(--mee-color-*)` or mee-* Tailwind classes — no hex literals
- 5-check matrix table uses native `<table>` with `role="table"` aria semantics
- ZERO `primeng/...` imports — boundary enforced

---

## 8. Out of Scope

| Item | Deferred to |
|---|---|
| Real multipart HTTP upload via ApiClient | Wave 6 API wiring |
| Upload progress % (HttpEvent stream) | Wave 6 — ApiClient.postMultipart returns Observable<T> not event stream |
| Actual Celery/GCS poll via GET | Wave 6 |
| Image reorder (drag to change slot order) | V1.5 |
| Image delete (remove a slot) | V1.5 |
| Gemini watermark check result surface | V1 — simulated as pass |

---

## 9. Verification Gates

| Gate | Check | Pass condition |
|---|---|---|
| 1 BUILD | `cd frontend && pnpm run build` | Zero errors, zero new warnings |
| 2 ROUTE | Navigate to `/catalogs/test-id/images` | ImageUploaderComponent renders in shell |
| 3 UPLOAD SIMULATION | Drop 4 mock files | Tiles appear, progress bars animate, slot 1 shows CMYK fail badge |
| 4 TESTS | `pnpm run test` | Min 4 tests pass (renders, canContinue false when any fail, hint text present, expand toggle) |
| 5 VISUAL | Review at 360px + 1280px | 2-col tile grid mobile; 3-col desktop; CMYK fail badge red; pass badge green |

---

## 10. Paste-Ready Dispatch Block

```
════════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER DISPATCH
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — F9 IMAGES (/catalogs/:id/images)
Agent: meesell-angular-component-builder
════════════════════════════════════════════════════════════════════

CONTEXT
───────
Waves 3+4 are complete. UI Kit (mee-* primitives) and composites
are stable. This dispatch builds the Images feature page (F9).
Simulate all API calls — no HttpClient wiring yet (Wave 6).

ROUTE: /catalogs/:id/images (shell child)
COMPONENT: ImageUploaderComponent

════════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  src/app/features/images/image-uploader/image-uploader.component.ts
  src/app/features/images/image-uploader/image-uploader.component.spec.ts
  src/app/features/images/image-uploader/image-uploader.model.ts

════════════════════════════════════════════════════════════════════

UI KIT USAGE
────────────
  mee-file-upload   → drag-drop zone (accept image/*, multiple, max 5MB)
  mee-progress-bar  → per-image pre-check animation (0→100)
  mee-badge         → per-check pass/fail (severity success|danger)
  mee-card          → image tile wrapper
  mee-button        → Re-upload (secondary/sm) + Continue CTA (primary)
  mee-page-header   → title + subtitle
  mee-status-badge  → slot overall status
  mee-loading-skeleton → card variant while polling

════════════════════════════════════════════════════════════════════

5-CHECK MATRIX (Feature 5 — V1_FEATURE_SPEC.md)
────────────────────────────────────────────────
  1. JPEG format         → jpeg_format: boolean
  2. RGB color space     → color_space_rgb: boolean (CMYK = false)
  3. Min resolution      → min_resolution: boolean (≥1500×1500)
  4. White BG            → white_bg: boolean
  5. No watermark        → no_watermark: boolean

SIMULATE: slot index 1 fails color_space_rgb (CMYK). All others pass.
Fix hint: "Convert image to RGB mode before uploading (CMYK detected)"

════════════════════════════════════════════════════════════════════

SIGNALS
───────
  images = signal<ProductImage[]>([])
  uploading = signal<boolean>(false)
  pollingActive = signal<boolean>(false)
  expandedSlot = signal<number | null>(null)
  canContinue = computed(() => images all pass && length > 0)

════════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────
  • standalone + OnPush + signals + inject()
  • NO Reactive Forms
  • ZERO primeng/... imports
  • Design tokens only (no hex literals)
  • 44px touch targets on all interactive controls
  • Clear setInterval in ngOnDestroy

════════════════════════════════════════════════════════════════════

VERIFICATION GATES
──────────────────
  Gate 1 BUILD: pnpm run build → zero errors
  Gate 2 ROUTE: /catalogs/:id/images renders in shell
  Gate 3 SIM:   slot 1 shows CMYK fail badge + fix hint
  Gate 4 TESTS: ≥4 tests pass
  Gate 5 VISUAL: 360px 2-col tiles; 1280px 3-col tiles

════════════════════════════════════════════════════════════════════
END DISPATCH
════════════════════════════════════════════════════════════════════
```
