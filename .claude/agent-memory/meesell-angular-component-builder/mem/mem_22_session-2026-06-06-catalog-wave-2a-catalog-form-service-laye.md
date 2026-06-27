## Session 2026-06-06 — Catalog Wave 2a — catalog-form service layer {#catalog-wave-2a}

### Route touched
`/catalogs/:id/edit` — features/catalog-form/

### Services consumed / created
All feature-scoped (`@Injectable()` NO `providedIn`):
- `CatalogFormApiService` (replaced stub)
- `DraftRecoveryService` (new)
- `CategorySchemaService` (new)
- `EnumLookupService` (new)
- `CatalogFormStateService` (new)

### Pattern: Feature-local model types for API contract drift
When `@core/models/*.model.ts` shape differs from the actual API response:
- Define a feature-local interface inline in the service file (e.g. `ProductDetail` in `catalog-form-api.service.ts`)
- Add a `// TODO(cross-cutting): reconcile` comment pointing to the core model to fix
- NEVER import the drifted core model and cast/transform it — that silently perpetuates the wrong shape
- Corollary: the autofill response `AutofillResponse` and draft `ProductDraft` are NEW types
  that don't exist in core models yet — also defined inline with the same TODO pattern

### Pattern: 204 handling for DraftRecoveryService
- `GET /products/:id/draft` returns 204 (no body) when product was never autosaved — common path
- `ApiClient.get<T>()` passes through null body from 204 response as `null`
- In the service: `pipe(map(res => res ?? null))` converts the null body cleanly to typed null
- ALSO add a `catchError` guard for the edge case where some HTTP adapters throw on 204
  (`if (err instanceof ApiError && err.status === 204) return of(null)`)
- In spec: mock with `apiClient.get.mockReturnValue(of(null))` — no need for complex HttpResponse wrapping

### Pattern: spec for services with no template (service-only spec)
- These services have NO template/component — use `TestBed.configureTestingModule({ providers: [...] })`
  without any `imports:[]` (no TranslocoTestingModule needed, no provideAnimationsAsync)
- Mock `ApiClient` as a plain object: `{ get: vi.fn(), post: vi.fn(), patch: vi.fn() }`
- `TestBed.inject(SomeService)` works cleanly for service-only TestBed configs
- Service-only specs are dramatically simpler than component specs

### Pattern: PrimitiveKind and StepId are string union types, NOT TypeScript enums
- `PrimitiveKind` = `'text_short' | 'text_long' | ...` (string union, no dot notation)
- `StepId` = `'basics' | 'pricing' | ...` (string union)
- Do NOT use `PrimitiveKind.TextInput` in specs — this is undefined at runtime
- Use string literals directly: `primitive: 'text_short'`, `stepId: 'basics'`
- Pattern confirmed from `@shared/enums/primitive-kind.enum.ts` and `step-id.enum.ts`

### Pattern: signal-based state service (no BehaviorSubject/Observable)
Per §16.B state management tree for per-route feature state:
- Signals for all state (NOT BehaviorSubject) — fresh instance per route activation
- `computed()` for derived values — they re-evaluate automatically when dependencies change
- Mutation methods produce new objects via spread (`{ ...current, [key]: newVal }`) — signals
  are not reactive objects; must SET a new reference for reactivity to propagate
- `acceptAiSuggestion` pattern: apply value via `applyFieldChange`, then destructure-remove
  from the suggestions Record (`const { [key]: _removed, ...rest } = suggestions`)
- `applyAutofillSuggestions` pattern: iterate `Object.entries()`, build new Record, spread-merge
  over existing suggestions

### Pattern: X-Autosave header verification in spec
The most critical correctness test in this dispatch. Verify with:
```typescript
const [path, body, options] = apiClient.patch.mock.calls[0];
expect(options?.headers?.['X-Autosave']).toBe('true');
```
AND separately for saveProduct:
```typescript
expect(options).toBeUndefined();  // saveProduct must NOT send any options
```

### CategorySchema model drift
`@core/models/category.model.ts#CategorySchema` is missing `categoryName: string`.
The actual API response includes it. Feature-local `CategorySchemaFull` defined in
`category-schema.service.ts` adds `categoryName`. TODO(cross-cutting) comment present.
Cross-cutting session should add `categoryName: string` to the core model.

### Build result (2026-06-06 Wave 2a)
- catalog-form-component lazy chunk: 7.70 kB raw / 2.29 kB gzip
- catalog-form-routes lazy chunk: 2.94 kB raw / 951 bytes gzip
- 24/24 new tests passing (5 spec files)
- ng build --configuration=production: ZERO errors

---
