# WAVE 5 — CATALOG FORM — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Feature Pages |
| **Date authored** | 2026-06-09 |
| **Status** | READY TO DISPATCH |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | meesell-angular-component-builder (sonnet) |
| **Agent** | meesell-angular-component-builder |
| **Depends on** | Wave 3 UI Kit complete + Wave 4 composites complete |

---

## 1. Module Summary

| Field | Value |
|---|---|
| **Route** | `/catalogs/:id/edit` (shell child — auth-guarded) |
| **Component class** | `CatalogFormComponent` |
| **Selector** | `app-catalog-form` |
| **Feature path** | `src/app/features/catalog-form/catalog-form.component.ts` |
| **Purpose** | Renders a dynamic category-specific field form from JSONB schema; AI auto-fill highlights compulsory fields in yellow; autosaves on blur/change |
| **Status** | F8 — NOT BUILT (Wave 5 target) |
| **V1 spec ref** | Feature 3 (Fast Catalog Form), Feature 4 (AI Auto-fill), §3 step 6, §5 GET /categories/{id}/schema + POST /products + PATCH /products/{id} + POST /products/{id}/autofill, §6 /catalogs/:id/edit |

---

## 2. Dependencies

### UI Kit Primitives (Layer 2 — from `../../ui`)
| Primitive | Selector | Used for |
|---|---|---|
| MeeInputComponent | `mee-input` | Field schema type `text_short`, `number`, `phone`, `email` |
| MeeTextareaComponent | `mee-textarea` | Field schema type `text_long` |
| MeeSelectComponent | `mee-select` | Field schema type `enum` (fixed option list) |
| MeeButtonComponent | `mee-button` | "AI fill" CTA; "Save" explicit save; "Next" navigation |
| MeeToastComponent + MeeToastService | `mee-toast` | Autosave confirmation ("Saved") + error notifications |

### Composites (Layer 3 — from `../../shared`)
| Composite | Selector | Used for |
|---|---|---|
| MeePageHeaderComponent | `mee-page-header` | Product name + breadcrumb + status badge |
| MeeStatusBadgeComponent | `mee-status-badge` | Current product status (draft / ready) in header |
| MeeLoadingSkeletonComponent | `mee-loading-skeleton` | Schema loading state (text variant ×8) |

### Layout
Shell child — `CatalogFormComponent` renders inside `MeeShellComponent` via `<router-outlet>`. No layout wrapping needed inside the component.

### API Endpoints (V1_FEATURE_SPEC.md §5)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/categories/{id}/schema` | Returns field schema for the selected category (JSONB) |
| POST | `/api/v1/products` | Creates draft product (called if arriving from smart-picker without a product ID — graceful handle) |
| PATCH | `/api/v1/products/{id}` | Autosave — sends changed field key/value pairs |
| POST | `/api/v1/products/{id}/autofill` | Triggers Gemini AI fill; returns suggested field values |

**Until API available: SIMULATE** schema with a 32-field Kurti schema (matching V1 spec §3 step 6 reference). Autosave simulates with `delay(300)`. Autofill simulates with `delay(2000)` + static suggestion payload covering 8 compulsory fields.

⚠️ BOUNDARY: import ONLY from `../../ui`, `../../shared`, `./services/`. ZERO `primeng/...` imports in this feature.

---

## 3. Files to Create / Modify

| File | Action |
|---|---|
| `features/catalog-form/catalog-form.component.ts` | CREATE — full page component |
| `features/catalog-form/catalog-form.component.spec.ts` | CREATE — minimum 6 tests |
| `features/catalog-form/services/catalog-form-api.service.ts` | CREATE — feature-scoped |
| `features/catalog-form/models/field-schema.model.ts` | CREATE — FieldSchema + FieldGroup types |

Do NOT modify `app.routes.ts` — `/catalogs/:id/edit` route exists from Wave 2B scaffold.

---

## 4. Component Spec

### ASCII Sketch — 360px mobile-first

```
┌─────────────────────────────────────────┐
│ [shell: sidebar collapsed / topbar]     │  ← MeeShellComponent (parent)
├─────────────────────────────────────────┤
│  Blue Cotton Kurti      [draft]         │  ← mee-page-header
│  Fashion > Women > Ethnic > Kurti       │    [subtitle]="category path"
│                         [ AI fill ]     │  ← mee-button (secondary, top-right)
├─────────────────────────────────────────┤
│  (while loading schema)                 │
│  ░░░░░░░░░░░  ░░░░░░░░░░░░░░░░░░        │  ← mee-loading-skeleton ×8
├─────────────────────────────────────────┤
│  ─── Compulsory (12) ───                │  ← section heading (font-medium, token color)
│                                         │
│  Product Title *                        │  ← mee-input (label, required indicator)
│  ┌─────────────────────────────────┐   │    field type: text_short
│  │ Blue Cotton Kurti — Mirror Work │   │    [error] if touched+invalid
│  └─────────────────────────────────┘   │    AI highlight: bg-yellow-50 border-yellow-300
│                                         │
│  Brand *                               │  ← mee-input (text_short)
│  ┌─────────────────────────────────┐   │    AI-filled yellow highlight if suggested
│  │ Generic                         │   │    user edited → highlight clears
│  └─────────────────────────────────┘   │
│                                         │
│  Color *                               │  ← mee-select (enum type)
│  ┌─────────────────────────────────┐   │    options from schema.enum_options
│  │ Blue ▼                          │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Description *                         │  ← mee-textarea (text_long)
│  ┌─────────────────────────────────┐   │    [rows]="4"
│  │ Blue cotton kurti...            │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ... (8 more compulsory fields)         │
│                                         │
│  ─── Recommended (10) ───              │  ← collapsed by default on mobile
│  [ + Show recommended fields ]         │  ← toggle button (ghost variant)
│                                         │
│  ─── Optional (10) ───                 │  ← collapsed by default
│  [ + Show optional fields ]            │
│                                         │
│  ─────────────────────────────────     │
│  ✓ Saved 2s ago                        │  ← autosave indicator (signal-driven)
│  [ ← Back ]   [ Images → ]            │  ← navigation buttons (ghost / primary)
└─────────────────────────────────────────┘
```

**Desktop note (1280px):** form renders in a centered max-width container (680px). Compulsory, Recommended, Optional sections are always expanded on desktop. Sidebar is expanded (270px).

**AI-fill highlight mechanism:** When autofill returns suggestions, each affected field gets a CSS class `mee-ai-suggested` applied via `[class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"`. The class adds `background-color: var(--mee-color-warning-light, #fef9c3); border-color: var(--mee-color-warning)`. When the user edits the field (blur event emitted), `acceptAiSuggestion(field.canonical_name)` removes it from the suggestions map — the class binding evaluates false and the yellow styling disappears automatically.

### Dynamic Field Schema → mee-* Mapping Strategy

The category schema from `GET /categories/{id}/schema` returns an array of `FieldGroup` objects. Each group contains `FieldSchema` items with a `primitive` type. The component maps primitive types to `mee-*` components via an `@switch` block in the template:

```
schema.primitive      → mee-* component
──────────────────────────────────────────
text_short            → mee-input  (type="text")
text_long             → mee-textarea
number                → mee-input  (type="number")
enum                  → mee-select (options from schema.enum_options)
(any other / unknown) → mee-input  (type="text", graceful fallback)
```

Each rendered field receives:
- `[label]="field.display_name"` (from schema)
- `[error]="getFieldError(field.canonical_name)"` (computed from touched + validation state)
- `[hint]="field.help_text"` (from XLSX-populated schema)
- `(blur or value_change event)` → `onFieldBlur(field.canonical_name, $event)` → triggers autosave debounce

Field values are stored in a plain `Record<string, unknown>` signal — NOT a `FormGroup`. Dynamic fields cannot be typed at compile time; the record approach is intentional.

### Signals / State
```typescript
readonly loading         = signal(true);
readonly schema          = signal<FieldGroup[]>([]);
readonly fieldValues     = signal<Record<string, unknown>>({});
readonly aiSuggestions   = signal<Record<string, unknown>>({});  // key = canonical_name
readonly saveStatus      = signal<'idle' | 'saving' | 'saved' | 'error'>('idle');
readonly autofilling     = signal(false);
readonly compulsoryOpen  = signal(true);
readonly recommendedOpen = signal(false);
readonly optionalOpen    = signal(false);
readonly productId       = signal<string>('');
```

### Computed
```typescript
readonly isFormComplete = computed(() =>
  compulsoryFields().every(f => !!fieldValues()[f.canonical_name])
);

// Helper method (not signal) — called from template
isAiSuggested(canonicalName: string): boolean {
  return canonicalName in this.aiSuggestions();
}
```

### Behaviors
- On init: read `:id` from `ActivatedRoute.snapshot.params`. Call `getSchema(categoryId)`. Set `productId`.
- On schema resolve: render all field groups. Open compulsory section; collapse others.
- On field change (blur): call `onFieldBlur(name, value)` — update `fieldValues()`, debounce 10 s → PATCH autosave. Also trigger autosave immediately on any blur event (debounce resets per blur).
- Autosave indicator: `saveStatus()` drives inline text "Saving…" / "Saved" / "Error". Reset to "idle" after 3 s post-save.
- "AI fill" click: set `autofilling(true)`, call `POST /products/:id/autofill` (simulated), receive suggested map, set `aiSuggestions()`, update `fieldValues()` with suggestions, set `autofilling(false)`.
- User edits an AI-suggested field: remove that key from `aiSuggestions()` on next blur (accept implicit by editing).
- Compulsory section toggle: `compulsoryOpen.set(!compulsoryOpen())` — always visible on desktop via CSS class.
- "Next — Images" navigation: `router.navigate(['/catalogs', productId(), 'images'])`.

---

## 5. UI Kit Usage Map

| UI element | mee-* component | Key @Input / @Output |
|---|---|---|
| Page title | `mee-page-header` | `[title]="productName()"` `[subtitle]="categoryPath()"` — no cta (AI fill is inline) |
| Product status | `mee-status-badge` | `[status]="'draft'"` — rendered inside header area |
| AI fill CTA | `mee-button` | `[label]="'AI fill'"` `[variant]="'secondary'"` `[icon]="'auto_awesome'"` `[loading]="autofilling()"` `(clicked)="onAutofill()"` |
| text_short field | `mee-input` | `[label]="field.display_name"` `[required]="field.required"` `[error]="getFieldError(field.canonical_name)"` `[hint]="field.help_text"` `[class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"` `(blur)="onFieldBlur(field.canonical_name, $event)"` |
| text_long field | `mee-textarea` | Same inputs as mee-input + `[rows]="4"` |
| enum field | `mee-select` | `[label]="field.display_name"` `[options]="field.enum_options"` `[error]="getFieldError(field.canonical_name)"` `(value_change)="onFieldChange(field.canonical_name, $event)"` |
| Loading state | `mee-loading-skeleton` | `[variant]="'text'"` `[lines]="3"` — shown `@if (loading())` |
| Autosave toast | `MeeToastService` | `toast.success('Saved')` on autosave success; `toast.error('Save failed')` on error |
| Section toggles | `mee-button` | `[variant]="'ghost'"` `[label]="'Show recommended fields'"` `(clicked)="recommendedOpen.set(true)"` |
| Navigation buttons | `mee-button` | Back: `[variant]="'ghost'"` `[label]="'Back'"` `(clicked)="onBack()"` · Next: `[label]="'Images'"` `[icon]="'arrow_forward'"` `(clicked)="onNext()"` |

---

## 6. API / Data

### GET /api/v1/categories/{id}/schema
**Response shape (expected):**
```typescript
interface FieldSchema {
  canonical_name: string;       // e.g. "product_title"
  display_name: string;         // e.g. "Product Title"
  primitive: 'text_short' | 'text_long' | 'number' | 'enum';
  required: boolean;
  help_text?: string;           // From XLSX inline help
  enum_options?: Array<{ label: string; value: string }>;
  max_length?: number;
  min_length?: number;
}

interface FieldGroup {
  group: 'compulsory' | 'recommended' | 'optional';
  fields: FieldSchema[];
}

type SchemaResponse = FieldGroup[];
```

**Simulation — 32-field Kurti schema:**
- Compulsory (12): product_title (text_short), brand (text_short), color (enum: Blue/Red/Yellow/Green/Pink/White), material (enum), pattern (enum), occasion (enum), fabric_care (text_short), description (text_long), size_type (enum: Free Size/S/M/L/XL/XXL), pack_of (number), country_of_origin (enum: India), model_name (text_short)
- Recommended (10): sleeve_length (enum), neck_type (enum), fit_type (enum), print_type (enum), closure_type (enum), wash_care (text_long), weight_grams (number), inner_lining (enum), item_height (number), item_width (number)
- Optional (10): fragrance (enum), sustainable_material (enum), frill_detail (text_short), embroidery_detail (text_short), dupatta_included (enum), waist_band (text_short), hem_detail (text_short), sleeve_detail (text_short), back_detail (text_short), additional_material (text_short)

**Autofill simulation response (POST /products/{id}/autofill):**
```typescript
// Simulate 8 compulsory fields filled by AI:
{
  product_title: 'Blue Cotton Kurti — Mirror Work',
  brand: 'Generic',
  color: 'Blue',
  material: 'Cotton',
  pattern: 'Mirror Work',
  occasion: 'Casual',
  fabric_care: 'Hand wash cold',
  description: 'Beautiful blue cotton kurti with intricate mirror work, perfect for casual and festive occasions.',
}
```
Simulate with `of(AUTOFILL_RESPONSE).pipe(delay(2000))`.

### PATCH /api/v1/products/{id} (autosave)
**Request body:** `{ fields_jsonb: Record<string, unknown> }` — partial update of changed fields only.
**Simulation:** `of(null).pipe(delay(300))`.

---

## 7. Constraints

| Rule | Detail |
|---|---|
| Standalone + OnPush | `@Component({ standalone: true, changeDetection: ChangeDetectionStrategy.OnPush })` |
| Signals for local state | `signal()` / `computed()` — no `BehaviorSubject` in component class |
| No PrimeNG imports | Feature imports ONLY from `../../ui`, `../../shared`, `@angular/core`, `@angular/router`, `@angular/forms`, rxjs |
| Dynamic fields NOT FormGroup | Field values held in `Record<string, unknown>` signal — NOT a reactive FormGroup. FormGroup cannot be typed for dynamic schema. |
| Autosave pattern | `Subject<void>` + `debounceTime(10_000)` + `takeUntilDestroyed(destroyRef)` in `ngOnInit`. Immediate blur also queues save. |
| 44px touch targets | All mee-button instances; mee-select trigger; section toggles min-height 44px |
| Design tokens only | AI highlight uses `var(--mee-color-warning-light)` + `var(--mee-color-warning)` — no hardcoded hex |
| Service scoping | `CatalogFormApiService`: `@Injectable()` no `providedIn` — feature route `providers:[]` |
| takeUntilDestroyed | `inject(DestroyRef)` explicitly; used in `ngOnInit` subscription context |
| File length budget | Component class MUST be ≤400 lines. Extract field-group section rendering to a sub-component if needed (`FieldGroupComponent`). |
| MeeToastService | Inject via `inject(MeeToastService)` — do NOT use MatSnackBar (Material not imported in features) |

---

## 8. Out of Scope

| Item | When |
|---|---|
| Real HTTP calls (schema fetch, autosave, autofill) | Wave 6 API wiring |
| `image_upload` primitive (file fields in schema) | Features/images handles this separately |
| Per-field AI diff overlay (accept/reject buttons per field) | V1.5 (see Feature 4 full spec) |
| Address group primitive (multi-subfield composite) | V1.5 |
| Category change mid-edit warning modal | V1.5 |
| Network offline queue for autosave | V1.5 |
| i18n (Tamil/Hindi labels) | V1.5 |
| "Accept all AI suggestions" bulk button | V1.5 |

---

## 9. Verification Gates

### Gate 1 — BUILD
```bash
cd frontend && pnpm run build
```
Pass: zero errors, zero new warnings.

### Gate 2 — ROUTES RESOLVE
```bash
cd frontend && pnpm start
```
Visit `http://localhost:4200/catalogs/mock-id/edit` — CatalogFormComponent renders; schema loads (simulated); field groups visible.

### Gate 3 — VALIDATION / INTERACTION
- Compulsory section renders with 12 fields (Kurti schema)
- Recommended / Optional sections are collapsed and toggle open on click
- Typing in "Product Title" field → blur → autosave status shows "Saving…" then "Saved"
- "AI fill" click → `autofilling()` true → after 2s → 8 fields highlight yellow
- Editing any yellow field → highlight removes on next blur
- "Images →" button navigates to `/catalogs/mock-id/images`

### Gate 4 — TESTS
```bash
cd frontend && pnpm run test
```
Minimum 6 tests:
1. Renders `mee-page-header` with subtitle containing category path
2. Shows `mee-loading-skeleton` while schema is loading
3. Compulsory section renders when schema resolves (check for "Compulsory" heading)
4. `onAutofill()` sets `autofilling(true)` before simulation completes
5. After autofill, `isAiSuggested('product_title')` returns true
6. Editing an AI-suggested field (`onFieldBlur('product_title', ...)`) removes it from `aiSuggestions()`

### Gate 5 — VISUAL (founder)
Founder reviews at 360px and 1280px:
- AI-filled fields highlighted in yellow (`var(--mee-color-warning-light)`)
- Compulsory asterisk visible on required fields
- Autosave "Saved" indicator appears and fades after 3 s
- "AI fill" button shows spinner while autofilling

---

## 10. Paste-Ready Dispatch Block

```
══════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER NOTIFICATION
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — CATALOG FORM (F8)  [MOST COMPLEX OF WAVE 5]
Agent: meesell-angular-component-builder (sonnet)
Depends on: Wave 3 UI Kit + Wave 4 Composites
══════════════════════════════════════════════════════════════════

CONTEXT
───────
Option A-full architecture. Catalog Form is a shell child.
This is the most complex Wave 5 feature.

Key architectural decision: dynamic fields use a Record<string, unknown>
signal — NOT a FormGroup — because field schema is runtime-defined JSONB.

API NOT available — simulate:
  schema: delay(800) + 32-field Kurti schema (compulsory 12 / recommended 10 / optional 10)
  autosave PATCH: delay(300) + of(null)
  autofill POST: delay(2000) + 8-field suggestion payload

BOUNDARY (enforced)
───────────────────
Import ONLY from:
  ../../ui            (mee-* UI Kit)
  ../../shared        (composites)
  ./services/         (CatalogFormApiService, feature-scoped)
  @angular/core, @angular/router, @angular/forms, rxjs

ZERO primeng/... imports in features/catalog-form/**.
ZERO MatSnackBar — use MeeToastService from ../../ui.

══════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  features/catalog-form/catalog-form.component.ts      (page component, ≤400 lines)
  features/catalog-form/catalog-form.component.spec.ts (min 6 tests)
  features/catalog-form/services/catalog-form-api.service.ts
  features/catalog-form/models/field-schema.model.ts   (FieldSchema, FieldGroup types)

══════════════════════════════════════════════════════════════════

COMPONENT SUMMARY
─────────────────
Route:    /catalogs/:id/edit (shell child)
Class:    CatalogFormComponent
Selector: app-catalog-form

Signals:
  loading, schema, fieldValues, aiSuggestions, saveStatus,
  autofilling, compulsoryOpen, recommendedOpen, optionalOpen, productId

Dynamic field schema → mee-* mapping:
  text_short  → mee-input  (type="text")
  text_long   → mee-textarea
  number      → mee-input  (type="number")
  enum        → mee-select (options from field.enum_options)
  (unknown)   → mee-input  (graceful fallback)

AI highlight mechanism:
  After autofill: set aiSuggestions() = { canonical_name: value, ... }
  Template: [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
  CSS class adds: bg var(--mee-color-warning-light), border var(--mee-color-warning)
  On field blur after edit: onFieldBlur() removes key from aiSuggestions()
  → yellow class binding evaluates false → highlight disappears

Autosave pattern:
  private readonly autosaveTrigger$ = new Subject<void>()
  In ngOnInit: autosaveTrigger$.pipe(debounceTime(10_000), takeUntilDestroyed(destroyRef)).subscribe(...)
  onFieldBlur(): update fieldValues(); autosaveTrigger$.next()
  saveStatus() signal: 'idle' → 'saving' → 'saved' (reset to 'idle' after 3s)

UI Kit used:
  mee-page-header    — product name + category path subtitle
  mee-status-badge   — draft/ready badge in header
  mee-button         — "AI fill" (secondary), section toggles (ghost), navigation
  mee-input          — text_short + number fields
  mee-textarea       — text_long fields
  mee-select         — enum fields
  mee-loading-skeleton — schema loading state
  MeeToastService    — autosave "Saved" toast + error notifications

Autofill simulation (POST /products/:id/autofill):
  8 compulsory fields pre-populated:
    product_title, brand, color, material, pattern,
    occasion, fabric_care, description

──────────────────────────────────────────────────────────────────

API (SIMULATED)
───────────────
GET  /api/v1/categories/{id}/schema
  → FieldGroup[] (compulsory/recommended/optional groups, each with FieldSchema[])
  Simulate: 32-field Kurti schema with delay(800)

PATCH /api/v1/products/{id}
  body: { fields_jsonb: Record<string, unknown> }
  → null (204)
  Simulate: of(null).pipe(delay(300))

POST /api/v1/products/{id}/autofill
  → Record<string, unknown> — suggested values keyed by canonical_name
  Simulate: 8-field map with delay(2000)

══════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────
  • standalone: true, changeDetection: OnPush
  • signal() for all local state — no BehaviorSubject in component
  • Dynamic fields: Record<string, unknown> signal — NOT FormGroup
  • CatalogFormApiService: @Injectable() no providedIn — route providers[]
  • DestroyRef injected explicitly — takeUntilDestroyed(destroyRef) in ngOnInit
  • File ≤ 400 lines — extract FieldGroupComponent if needed
  • 44px touch targets on all interactive elements
  • Design tokens only — AI highlight via var(--mee-color-warning-light)
  • MeeToastService — NOT MatSnackBar
  • ZERO primeng/... imports

OUT OF SCOPE
────────────
  ✗ Real HTTP calls (Wave 6)
  ✗ Per-field accept/reject overlay (V1.5)
  ✗ Address group composite field (V1.5)
  ✗ Network offline queue (V1.5)
  ✗ "Accept all" bulk button (V1.5)

VERIFICATION GATES
──────────────────
Gate 1 BUILD:      pnpm run build → zero errors
Gate 2 ROUTES:     /catalogs/mock-id/edit renders — schema fields visible
Gate 3 INTERACTION: field edit → autosave; AI fill → yellow highlights; blur → clears
Gate 4 TESTS:      pnpm run test → 6+ new tests passing
Gate 5 VISUAL:     ⏳ founder reviews AI-fill yellow highlight at 360px + 1280px

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```
