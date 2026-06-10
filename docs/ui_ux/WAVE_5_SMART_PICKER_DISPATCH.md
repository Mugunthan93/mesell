# WAVE 5 — SMART PICKER — DISPATCH NOTIFICATION

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
| **Route** | `/catalogs/new` (shell child — auth-guarded) |
| **Component class** | `SmartPickerComponent` |
| **Selector** | `app-smart-picker` |
| **Feature path** | `src/app/features/smart-picker/smart-picker.component.ts` |
| **Purpose** | Seller types product description; receives 3 ranked AI category suggestions; picks one; navigates to `/catalogs/:id/edit` |
| **Status** | F7 — NOT BUILT (Wave 5 target) |
| **V1 spec ref** | Feature 2 (Smart Category Picker), §3 step 5, §5 GET /api/v1/categories/suggest |

---

## 2. Dependencies

### UI Kit Primitives (Layer 2 — from `../../ui`)
| Primitive | Selector | Used for |
|---|---|---|
| MeeTextareaComponent | `mee-textarea` | Description free-text input (multi-line) |
| MeeButtonComponent | `mee-button` | "Suggest categories" submit CTA |
| MeeCardComponent | `mee-card` | Category suggestion card container (×3) |
| MeeProgressBarComponent | `mee-progress-bar` | Confidence % bar inside each category card |
| MeeTreeSelectComponent | `mee-tree-select` | Manual category fallback browse (optional — shown when no suggestions match) |
| MeeSkeletonComponent | `mee-skeleton` | Loading state while suggestions are fetching |

### Composites (Layer 3 — from `../../shared`)
| Composite | Selector | Used for |
|---|---|---|
| MeePageHeaderComponent | `mee-page-header` | "New Catalog" page title (no CTA button here) |
| MeeLoadingSkeletonComponent | `mee-loading-skeleton` | 3-card skeleton while API call runs (variant: card) |

### Layout
Shell child — `SmartPickerComponent` renders inside `MeeShellComponent` via `<router-outlet>`. No layout wrapping needed inside the component.

### API Endpoints (V1_FEATURE_SPEC.md §5)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/categories/suggest?q=<description>` | Returns top-3 category suggestions with confidence |
| POST | `/api/v1/products` | Creates a draft product once user picks a category |

**Until API available: SIMULATE** with 3 hardcoded suggestions matching the V1 spec §3 step 5 example (kurti scenario). Delay 1200 ms to simulate Gemini latency. Draft product creation simulates with `of({ id: 'draft-001', category_id: '...' }).pipe(delay(500))`.

⚠️ BOUNDARY: import ONLY from `../../ui`, `../../shared`, `./services/`. ZERO `primeng/...` imports in this file.

---

## 3. Files to Create / Modify

| File | Action |
|---|---|
| `features/smart-picker/smart-picker.component.ts` | CREATE — full page component |
| `features/smart-picker/smart-picker.component.spec.ts` | CREATE — minimum 5 tests |
| `features/smart-picker/services/smart-picker-api.service.ts` | CREATE — feature-scoped |

Do NOT modify `app.routes.ts` — `/catalogs/new` route exists from Wave 2B scaffold.

---

## 4. Component Spec

### ASCII Sketch — 360px mobile-first

```
┌─────────────────────────────────────────┐
│ [shell: sidebar collapsed / topbar]     │  ← MeeShellComponent (parent)
├─────────────────────────────────────────┤
│  New Catalog                            │  ← mee-page-header (title only)
├─────────────────────────────────────────┤
│  Describe your product                  │  ← label (text-sm font-medium)
│  ┌───────────────────────────────────┐  │
│  │ e.g. "Blue cotton kurti with      │  │  ← mee-textarea
│  │ mirror work for women, size M–XXL"│  │    rows=4, label, placeholder
│  └───────────────────────────────────┘  │
│  Describe in at least 10 characters     │  ← hint text (shown when <10 chars)
│                                         │
│  [ Suggest categories ]                 │  ← mee-button (primary, full-width)
│                                         │    [loading]="suggesting()"
│                                         │
│  ─── OR browse manually ─── (divider)   │
│  ┌───────────────────────────────────┐  │
│  │ Select category ▼                 │  │  ← mee-tree-select (collapsed by default)
│  └───────────────────────────────────┘  │
│                                         │
│  (while suggesting — loading state)     │
│  ░░░░░░░░░░░░░░░░░░░░░  (card skel ×3)  │  ← mee-loading-skeleton (card variant)
│                                         │
│  (after suggest — suggestion cards)     │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ Fashion > Women > Ethnic > Kurti  │  │  ← mee-card (suggestion #1)
│  │ Commission: 5 %                   │  │
│  │ ████████████████████░░ 94 %       │  │  ← mee-progress-bar (value=94)
│  │               [ Pick this ]       │  │  ← mee-button (secondary, sm)
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ Fashion > Women > Ethnic > Kurta  │  │  ← mee-card (suggestion #2)
│  │ Set                               │  │
│  │ Commission: 6 %                   │  │
│  │ █████████████████░░░░░ 71 %       │  │  ← mee-progress-bar (value=71)
│  │               [ Pick this ]       │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ Fashion > Women > Tops > Tunic    │  │  ← mee-card (suggestion #3)
│  │ Commission: 7 %                   │  │
│  │ ████████████░░░░░░░░░░ 52 %       │  │  ← mee-progress-bar (value=52)
│  │               [ Pick this ]       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Desktop note (1280px):** suggestion cards render side-by-side in a 3-column grid. Description textarea and suggest button remain full-width above the grid. Sidebar is expanded (270px).

### V1 Spec §3 Step 5 — Seed Data (canonical kurti example)
```typescript
const SIMULATED_SUGGESTIONS: CategorySuggestion[] = [
  {
    id: 'cat-kurti-uuid',
    path: 'Fashion > Women > Ethnic > Kurti',
    confidence: 94,
    commission_pct: 5,
  },
  {
    id: 'cat-kurta-set-uuid',
    path: 'Fashion > Women > Ethnic > Kurta Set',
    confidence: 71,
    commission_pct: 6,
  },
  {
    id: 'cat-tunic-uuid',
    path: 'Fashion > Women > Tops > Tunic',
    confidence: 52,
    commission_pct: 7,
  },
];
```

### Signals / State
```typescript
readonly description    = signal('');
readonly suggesting     = signal(false);
readonly suggestions    = signal<CategorySuggestion[]>([]);
readonly picking        = signal(false);         // draft product creation in-flight
readonly showFallback   = signal(false);         // manual tree-select shown
readonly errorMessage   = signal<string | null>(null);
```

### Form
```typescript
form = this.fb.group({
  description: ['', [Validators.required, Validators.minLength(10)]],
});
```

### Behaviors
- "Suggest categories" button disabled when `form.invalid || suggesting()`
- On submit: set `suggesting(true)`, call API (simulated), set `suggestions()`, set `suggesting(false)`
- Error (e.g. <10 chars bypass): show inline validation message
- "Pick this" button: set `picking(true)`, call `POST /api/v1/products` (simulated), navigate `/catalogs/:id/edit`
- "Browse manually" link: toggles `showFallback(true)` — shows `mee-tree-select`
- `mee-tree-select` `value_change` output → direct pick (same flow as "Pick this")
- If API returns empty suggestions: show "No matches — try a different description" + manual fallback auto-shown
- Min description length guard: Validators.minLength(10) — inline error below textarea when touched

---

## 5. UI Kit Usage Map

| UI element | mee-* component | Key @Input / @Output |
|---|---|---|
| Page title | `mee-page-header` | `[title]="'New Catalog'"` — no cta_label |
| Description input | `mee-textarea` | `[label]="'Describe your product'"` `[placeholder]="'e.g. Blue cotton kurti...'"` `[error]="descError()"` `formControlName="description"` |
| Suggest CTA | `mee-button` | `[label]="'Suggest categories'"` `[loading]="suggesting()"` `[disabled]="form.invalid"` `[fullWidth]="true"` `(clicked)="onSuggest()"` |
| Loading cards | `mee-loading-skeleton` | `[variant]="'card'"` — ×3, shown via `@if (suggesting())` |
| Suggestion card wrapper | `mee-card` | content projection — category path, commission, progress bar, pick button |
| Confidence bar | `mee-progress-bar` | `[value]="suggestion.confidence"` `[label]="suggestion.confidence + ' %'"` `[show_value]="true"` |
| Pick this button | `mee-button` | `[label]="'Pick this'"` `[variant]="'secondary'"` `[size]="'sm'"` `[loading]="picking()"` `(clicked)="onPick(suggestion)"` |
| Manual fallback | `mee-tree-select` | `[nodes]="categoryTree()"` `[placeholder]="'Select category'"` `[loading]="treeLoading()"` `(value_change)="onTreePick($event)"` |

---

## 6. API / Data

### GET /api/v1/categories/suggest?q=\<description\>
**Request:** `q` param = description string

**Response shape (expected):**
```typescript
interface CategorySuggestion {
  id: string;              // category UUID
  path: string;            // e.g. "Fashion > Women > Ethnic > Kurti"
  confidence: number;      // 0–100
  commission_pct: number;  // from categories table
}
type SuggestResponse = CategorySuggestion[];
```

**Simulation:** Return `SIMULATED_SUGGESTIONS` wrapped in `of([...]).pipe(delay(1200))`. Return empty array when description < 10 chars (trigger error state).

### POST /api/v1/products (create draft)
**Request body:**
```typescript
interface CreateProductRequest {
  category_id: string;
}
```

**Response shape (expected):**
```typescript
interface CreateProductResponse {
  id: string;    // product UUID — used for /catalogs/:id/edit navigation
  category_id: string;
  status: 'draft';
}
```

**Simulation:** Return `of({ id: 'draft-' + Date.now(), category_id: suggestion.id, status: 'draft' }).pipe(delay(500))`.

### mee-tree-select data (manual fallback)
Simulate a 2-level tree with 3 parent nodes + 2 leaf nodes each. This is a placeholder; real data comes from a categories endpoint not in V1 spec scope. Show `[loading]="true"` then set static tree after 600 ms delay.

---

## 7. Constraints

| Rule | Detail |
|---|---|
| Standalone + OnPush | `@Component({ standalone: true, changeDetection: ChangeDetectionStrategy.OnPush })` |
| Signals for local state | `signal()` / `computed()` — no `BehaviorSubject` in component class |
| No PrimeNG imports | Feature imports ONLY from `../../ui`, `../../shared`, `@angular/core`, `@angular/router`, `@angular/forms`, rxjs |
| 44px touch targets | All mee-button instances, mee-card pick buttons, mee-tree-select panel items |
| Reactive Forms only | `FormGroup` + `FormBuilder` via `inject(FormBuilder)` — no template-driven |
| Design tokens only | Colors via `var(--mee-color-*)` — no hardcoded hex in component |
| Service scoping | `SmartPickerApiService`: `@Injectable()` no `providedIn` — route `providers:[]` |
| takeUntilDestroyed | RxJS subscriptions in constructor use `takeUntilDestroyed()` |
| Min description | `Validators.minLength(10)` — matches V1 spec §2 Feature 2 edge case |

---

## 8. Out of Scope

| Item | When |
|---|---|
| Real Gemini-backed API call | Wave 6 API wiring |
| Real POST /api/v1/products | Wave 6 API wiring |
| Full 3,772-node category tree for mee-tree-select | Wave 6 (categories endpoint) |
| Hindi/Tamil description input | V1.5 |
| Confidence % explanation tooltip | V1.5 |
| Back navigation after pick (breadcrumb) | Shell handles via sidebar |

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
Visit `http://localhost:4200/catalogs/new` — SmartPickerComponent renders, textarea visible, button visible.

### Gate 3 — VALIDATION / INTERACTION
- Suggest button disabled when description empty or < 10 chars
- Inline error appears on blur when description < 10 chars
- Submit with valid description → skeleton cards appear → suggestion cards appear
- Confidence bars render with correct values (94 / 71 / 52)
- "Pick this" on first card → navigates to `/catalogs/draft-NNN/edit`
- Manual fallback toggle shows `mee-tree-select`

### Gate 4 — TESTS
```bash
cd frontend && pnpm run test
```
Minimum 5 tests:
1. Renders `mee-page-header` with title "New Catalog"
2. "Suggest categories" button disabled when description is empty
3. "Suggest categories" button disabled when description has fewer than 10 characters
4. `onSuggest()` sets `suggesting(true)` during in-flight simulation
5. `onPick(suggestion)` calls `router.navigate` with `/catalogs/{id}/edit`

### Gate 5 — VISUAL (founder)
Founder reviews at 360px and 1280px:
- 3 suggestion cards showing kurti/kurta-set/tunic paths
- Confidence bars colored in MeeSell orange (`var(--mee-color-primary)`)
- 94% bar clearly fuller than 52% bar
- Manual fallback tree-select renders below divider

---

## 10. Paste-Ready Dispatch Block

```
══════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER NOTIFICATION
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — SMART PICKER (F7)
Agent: meesell-angular-component-builder (sonnet)
Depends on: Wave 3 UI Kit + Wave 4 Composites
══════════════════════════════════════════════════════════════════

CONTEXT
───────
Option A-full architecture. Smart Picker is a shell child.
API NOT available — simulate:
  suggestions: delay(1200) + SIMULATED_SUGGESTIONS (kurti example from V1 spec §3 step 5)
  product draft: delay(500) + of({ id: 'draft-' + Date.now(), ... })
  tree-select data: static 2-level stub after 600ms

BOUNDARY (enforced)
───────────────────
Import ONLY from:
  ../../ui            (mee-* UI Kit)
  ../../shared        (composites)
  ./services/         (SmartPickerApiService, feature-scoped)
  @angular/core, @angular/router, @angular/forms, rxjs

ZERO primeng/... imports in features/smart-picker/**.

══════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  features/smart-picker/smart-picker.component.ts      (page component)
  features/smart-picker/smart-picker.component.spec.ts (min 5 tests)
  features/smart-picker/services/smart-picker-api.service.ts

══════════════════════════════════════════════════════════════════

COMPONENT SUMMARY
─────────────────
Route:    /catalogs/new (shell child)
Class:    SmartPickerComponent
Selector: app-smart-picker

Form:
  description: ['', [Validators.required, Validators.minLength(10)]]

Signals:
  suggesting, suggestions, picking, showFallback, errorMessage

UI Kit used:
  mee-page-header    — title "New Catalog"
  mee-textarea       — description input (formControlName)
  mee-button         — "Suggest categories" (primary, full-width, [loading]="suggesting()")
  mee-card           — ×3 suggestion cards (content projection)
  mee-progress-bar   — confidence % per card (value 0–100)
  mee-button (sm)    — "Pick this" per card ([loading]="picking()")
  mee-loading-skeleton — while suggesting (card variant ×3)
  mee-tree-select    — manual fallback browse (shown when showFallback())

Journey example (V1 spec §3 step 5):
  User types: "Blue cotton kurti with mirror work for women, size M to XXL"
  Result cards:
    1. Fashion > Women > Ethnic > Kurti     → 94% confidence, commission 5%
    2. Fashion > Women > Ethnic > Kurta Set → 71% confidence, commission 6%
    3. Fashion > Women > Tops > Tunic       → 52% confidence, commission 7%

Flow:
  Pick card → POST /api/v1/products (simulated) → navigate /catalogs/:id/edit
  Tree-select pick → same flow

──────────────────────────────────────────────────────────────────

API (SIMULATED)
───────────────
GET /api/v1/categories/suggest?q=<description>
  → CategorySuggestion[] (id, path, confidence, commission_pct)
  Simulate: of(SIMULATED_SUGGESTIONS).pipe(delay(1200))

POST /api/v1/products
  body: { category_id: string }
  → { id: string, category_id: string, status: 'draft' }
  Simulate: of({ id: 'draft-' + Date.now(), ... }).pipe(delay(500))

══════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────
  • standalone: true, changeDetection: OnPush
  • signal() for all local state
  • SmartPickerApiService: @Injectable() no providedIn — route providers[]
  • takeUntilDestroyed() for RxJS in constructor
  • Validators.minLength(10) on description — V1 spec edge case
  • 44px touch targets on all interactive elements
  • var(--mee-color-*) tokens — no hardcoded hex
  • ReactiveFormsModule — no template-driven

OUT OF SCOPE
────────────
  ✗ Real HTTP calls (Wave 6)
  ✗ Full 3,772-node category tree (Wave 6)
  ✗ Hindi/Tamil input support (V1.5)

VERIFICATION GATES
──────────────────
Gate 1 BUILD:      pnpm run build → zero errors
Gate 2 ROUTES:     /catalogs/new renders — textarea + button visible
Gate 3 INTERACTION: suggest → skeleton → 3 cards; pick → navigate
Gate 4 TESTS:      pnpm run test → 5+ new tests passing
Gate 5 VISUAL:     ⏳ founder reviews kurti cards at 360px + 1280px

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```
