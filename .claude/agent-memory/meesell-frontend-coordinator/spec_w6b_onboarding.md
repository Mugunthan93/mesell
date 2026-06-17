---
name: spec-w6b-onboarding
description: HYBRID step-1 TASK SPEC for Wave 6 Wave B lane 2 (wave6-onboarding) — extract a SellerProfileService from the inline mocks in mfe-onboarding and wire the real customer endpoints (#7 get, #8 patch, #9 active-categories, #10 compliance, #11 required-fields). Consumes the Wave-A-frozen shared surface. SPEC ONLY — no code, no dispatch, no git. CONTAINS A P0 CONTRACT-MISMATCH STOP-FINDING (§2.6) the master/founder must rule on BEFORE the build dispatch.
metadata:
  type: project
  session: mesell-wave6-b-specs-session-1
  status: SPEC — BLOCKED on a founder ruling (§2.6) before step-2 dispatch
  base: feature/wave6-onboarding/integration cut from POST-#135 develop
  parallel_lane_peer: spec_w6b_dashboard.md (mfe-dashboard) — FILE-DISJOINT
---

# Wave 6 · Wave B — lane 2 — `wave6-onboarding` — TASK SPEC

> HYBRID step-1 deliverable. The session window dispatches the named specialists (step 2) with this spec; I am re-dispatched for the merge gate (step 3). I wrote NO feature code, called NO Task, ran NO git this session.
>
> **⛔ READ §2.6 FIRST.** This lane has a P0 contract mismatch: the as-built onboarding/profile UI collects fields (`businessName`, `city`, `gstNumber`, display `name`) that DO NOT EXIST in the real backend customer module (which is entirely Legal-Metrology compliance fields). This is NOT ordinary mock→real wiring. The lane CANNOT be dispatched as a pure wiring slice until the founder rules on §2.6.

## 0. Governing context — Wave A is the FROZEN floor

Branches from **post-#135 develop** (Wave A `wave6-auth-core` tip `fcb9ceb`). Wave A FROZE the shared surface. **This slice MUST NOT modify any of it** (§7 parallel-lane discipline):

| Wave-A frozen surface (do NOT edit) | What this slice consumes |
|---|---|
| `libs/core/interceptors/{jwt,refresh,error}.interceptor.ts` | Global Bearer attach + 401→refresh→retry + error normalisation. Registered in `apps/mfe-onboarding/src/main.ts` by Wave A. NO manual auth headers in this slice. |
| `libs/core/services/api-client.service.ts` (`ApiClient`) | The typed wrapper (`get`/`patch<T>`). The new `SellerProfileService` SHOULD use it. Confirm the as-merged surface at dispatch. |
| `libs/core/services/error.service.ts` / `network.service.ts` | Global error surface (interceptor-fed) + `online` signal (offline banner). |
| `libs/core/services/auth.service.ts` (`AuthService`, `AuthUser` additive-optional) | `currentUser()` (profile identity card reads `name`/`phone`/`plan`); `logout()` (profile log-out button). `AuthUser.name` is now OPTIONAL (Wave A) — the profile template `auth.currentUser()?.name \|\| 'Seller'` still compiles (it already used `?.` + fallback). `plan?` is now available for the plan badge (currently hardcoded "Free plan"). |
| `@mesell/composites` `MeeAlertBanner` + `MeeOfflineBanner` (NEW in Wave A) + `AuthLayoutComponent` (existing) | Error/offline banners (§6) + the auth-layout wrapper onboarding already uses. Confirm banner selectors/inputs at dispatch. |
| `apps/mfe-onboarding/src/main.ts` | Wave A ADDED `provideHttpClient(withFetch(), withInterceptors([...]))`. **Do NOT touch main.ts** (Wave-A-frozen + parallel-lane tripwire). main.ts already routes BOTH exposes (Onboarding+Profile) for the singleton graph (R-SP3-1) — leave it. |

**If ANY frozen surface needs a change → STOP and escalate (§10).**

## 1. Slice identity & scope

- **Slice:** `wave6-onboarding` (Wave 6, Wave B, lane 2 — parallel with `wave6-dashboard`).
- **Remote:** `apps/mfe-onboarding` ONLY (port 4202). FILE-DISJOINT from lane 1 (`apps/mfe-dashboard`).
- **V1 routes exercised:** `/onboarding` (OnboardingComponent) + `/profile` (ProfileComponent).
- **Endpoints (customer module — verified §2):** **#7** `GET /seller-profile`, **#8** `PATCH /seller-profile`, **#9** `PATCH /seller-profile/active-categories`, **#10** `PATCH /seller-profile/compliance/{super_id}`, **#11** `GET /seller-profile/required-fields`. All JWT, all `response_model=SellerProfileResponse` except #11 (`RequiredFieldsResponse`).
- **Specialists:** `meesell-angular-service-builder` (PRIMARY — extract a NEW `SellerProfileService`, currently NO service exists — both pages use inline `setTimeout`; wire the real endpoints; degradation matrix + specs) → `meesell-angular-component-builder` (wire onboarding + profile forms to the service; loading/error/offline states; **reconcile the form fields per the §2.6 ruling**) → `meesell-angular-ui-styler` (error/offline polish, screenshots). Serial (§8). **service-builder is REQUIRED here** (unlike a swap-only lane) — there is no service to swap; one must be created (a genuine extraction).

### Scope IN (this slice only — all under `apps/mfe-onboarding/`)
- `apps/mfe-onboarding/src/app/services/seller-profile.service.ts` (NEW — does not exist; the extraction)
- `apps/mfe-onboarding/src/app/seller-profile.model.ts` (NEW — remote-private TS interfaces transcribed from §2)
- `apps/mfe-onboarding/src/app/onboarding.component.ts` (EDIT — replace inline `setTimeout`; wire submit → PATCH; **field reconciliation per §2.6**)
- `apps/mfe-onboarding/src/app/profile.component.ts` (EDIT — replace inline `setTimeout`; load profile on init; wire submit → PATCH; **field reconciliation per §2.6**)
- `apps/mfe-onboarding/src/app/onboarding.component.spec.ts` + `profile.component.spec.ts` (EDIT — assert real flow + states)
- `apps/mfe-onboarding/src/app/services/seller-profile.service.spec.ts` (NEW — `HttpTestingController`)
- `apps/mfe-onboarding/src/app/auth-singleton.smoke.spec.ts` — **NO assertion change** (the C5 singleton smoke; touch only if the AuthUser-additive change requires an annotation — STOP if it needs an ASSERTION rewrite, that signals drift).

### Scope OUT (defer / STOP)
- Any `backend/` change → **STOP** (§10).
- `@mesell/core`, interceptors, composites-source, ANY remote `main.ts`, `apps/shell/**` → Wave-A FROZEN. Touch = STOP.
- `apps/mfe-dashboard/**` (lane 1) → DISJOINT, never touch.
- `app.routes.ts` route tables → frozen.
- The compliance-extension UI (#10 `PATCH .../compliance/{super_id}`) is a MULTI-STEP wizard surface that the as-built onboarding does NOT have — see §2.6/§3. V1 onboarding may wire only the base-profile PATCH (#8) + required-fields (#11) and defer the per-super compliance forms — founder's call in §2.6.

---

## 2. Ground-truth contract (cited file:line — NO invented shapes)

All paths under `/api/v1`. Customer module verified on `origin/develop` @ `b622847` (backend unchanged by #135).

### 2.1 Endpoint map — `backend/app/modules/customer/router.py` (prefix `/api/v1`, L69)

| # | Method · Path (router.py L) | Request | Response (`response_model=`) |
|---|---|---|---|
| 7 | `GET /seller-profile` (L75-77 path L76) | — | `SellerProfileResponse` (L77) |
| 8 | `PATCH /seller-profile` (L101-103 path L102) | `PatchProfileRequest` | `SellerProfileResponse` (L103) |
| 9 | `PATCH /seller-profile/active-categories` (L129-131 path L130) | `PatchActiveCategoriesRequest` | `SellerProfileResponse` (L131) |
| 10 | `PATCH /seller-profile/compliance/{super_id}` (L158-160 path L159) | `PatchComplianceExtensionRequest` | `SellerProfileResponse` (L160) |
| 11 | `GET /seller-profile/required-fields` (L198-200 path L199) | — | `RequiredFieldsResponse` (L200) |

### 2.2 `SellerProfileResponse` (#7/#8/#9/#10 response) — `customer/schemas.py` class `SellerProfileResponse`

```
SellerProfileResponse:
  user_id: UUID                        -> string
  manufacturer_name: str | None        -> string | null
  manufacturer_address: str | None     -> string | null
  manufacturer_pincode: str | None     -> string | null
  packer_name: str | None              -> string | null
  packer_address: str | None           -> string | null
  packer_pincode: str | None           -> string | null
  importer_name: str | None            -> string | null
  importer_address: str | None         -> string | null
  importer_pincode: str | None         -> string | null
  country_of_origin: str = "India"     -> string
  active_super_categories: list[str]   -> string[]
  compliance_extensions: dict[str, dict[str, Any]]  -> Record<string, Record<string, unknown>>
  onboarding_complete: bool            -> boolean
  created_at: datetime                 -> string
  updated_at: datetime                 -> string
```

### 2.3 `PatchProfileRequest` (#8 body — all OPTIONAL, subset semantics) — `customer/schemas.py` class `PatchProfileRequest`

```
PatchProfileRequest (extra="forbid"):
  manufacturer_name: str | null
  manufacturer_address: str | null
  manufacturer_pincode: str | null   (pattern ^\d{6}$)   -> 422 validation.pincode.invalid_format on bad PIN
  packer_name: str | null
  packer_address: str | null
  packer_pincode: str | null         (pattern ^\d{6}$)
  importer_name: str | null
  importer_address: str | null
  importer_pincode: str | null       (pattern ^\d{6}$)
  country_of_origin: str | null
```
`active_super_categories` has its OWN endpoint (#9); `compliance_extensions` has its OWN (#10).

### 2.4 `PatchActiveCategoriesRequest` (#9) — `class PatchActiveCategoriesRequest`
`{ active_super_categories: string[] }` (`min_length=1` — empty array rejected at schema time; `extra="forbid"`). REPLACES the array entirely (not additive).

### 2.5 `RequiredFieldsResponse` (#11 — drives the onboarding wizard) — `class RequiredFieldsResponse`

```
RequiredFieldsResponse:
  base_fields: list[dict[str, Any]]                       -> FieldSpec[]   (§5A.C FieldSpec contract — same convention as the catalog wizard)
  extension_fields: dict[str, list[dict[str, Any]]]       -> Record<super_id, FieldSpec[]>
  completed: dict[str, bool]                              -> Record<string, boolean>  (dot-path keys e.g. "manufacturer_name", "ext.26.fssai_license_number")
```
`FieldSpec` entries are `dict[str, Any]` at the schema layer (Pydantic-on-3.11 TypedDict constraint, schemas.py NOTE) — the §5A.C-shaped keys. **The FE must read the actual FieldSpec key set from the live `/required-fields` response shape (or the i18n `schema_contract.FieldSpec` TypedDict) before authoring the TS `FieldSpec` interface** — do NOT invent FieldSpec keys (§10 stop / cross-lead memo to backend if the key set is ambiguous).

### 2.6 ⛔ P0 CONTRACT MISMATCH — the as-built UI vs the real backend (FOUNDER RULING REQUIRED)

The as-built onboarding/profile UI was built against an INLINE MOCK whose field domain has **ZERO overlap** with the real customer module:

| As-built UI field (file:line) | Real backend equivalent | Status |
|---|---|---|
| `onboarding.component.ts` `businessName` (L127) | — | **DOES NOT EXIST** in customer schemas |
| `onboarding.component.ts` `city` (L128, default 'Tirupur') | — | **DOES NOT EXIST** |
| `onboarding.component.ts` `gstNumber` + `optionalGstValidator` (L129, L26-35) | — | **DOES NOT EXIST** (no GST field anywhere in customer module) |
| `profile.component.ts` `name` (L130) display-name edit | — | **DOES NOT EXIST** (no profile display-name; `AuthUser.name` is a legacy-mock field Wave A made optional) |
| — | `manufacturer_*`, `packer_*`, `importer_*` (9 Legal-Metrology fields), `country_of_origin`, `active_super_categories`, `compliance_extensions` | **The REAL onboarding domain — currently UN-collected by any UI** |

**This is not field-renaming — it is a different feature.** The real V1 onboarding is the **Legal Metrology compliance capture** (manufacturer/packer/importer name+address+6-digit-pincode, country of origin, active super-categories, per-super compliance extensions), driven by `GET /required-fields` (#11) which returns the FieldSpec wizard schema. The mock UI (business name / city / GST) is a DIFFERENT, simpler onboarding that the backend does not support.

**STOP. This lane CANNOT be dispatched as pure wiring.** Wiring `onSubmit` of the current form to `PATCH /seller-profile` would send `{businessName, city, gstNumber}` → the backend `PatchProfileRequest` has `extra="forbid"` → **immediate 422** (all three keys are rejected). The forms must be REBUILT to the real domain, which is a component-construction task (new fields, the FieldSpec-driven wizard, pincode validators, the active-categories picker), NOT an API-swap.

**FOUNDER RULING REQUIRED (escalated via §12 memo + STATUS_MASTER) — three options:**

- **OPTION A (RECOMMENDED — rebuild onboarding to the real domain, scoped to base profile):** treat `wave6-onboarding` as a build-AND-wire slice. Rebuild the onboarding form to capture the **base SellerProfile** fields (manufacturer + packer name/address/pincode + country_of_origin) driven by `GET /required-fields` base_fields, submit via `PATCH /seller-profile` (#8). Rebuild the profile page to LOAD `GET /seller-profile` (#7) and edit the same base fields. **DEFER** the per-super `compliance_extensions` wizard (#10) and the `active-categories` picker (#9) to a follow-up slice (they are multi-step surfaces with their own UX). This keeps the slice bounded but real. The component-builder does meaningful construction (not just wiring) — flag the expanded component scope.
- **OPTION B (full onboarding wizard):** rebuild ALL of onboarding — base profile (#8) + active-categories picker (#9) + per-super compliance wizard (#10) + the FieldSpec renderer (#11). Larger; likely its own wave, not a Wave-B lane.
- **OPTION C (defer the whole lane):** the as-built mock UI is a placeholder; the real onboarding UX needs design first. Defer `wave6-onboarding` out of Wave B; run Wave B as dashboard-only (single lane) and schedule onboarding after a design pass. The mock stays (no white-screen risk — it never calls the backend).

**My recommendation: OPTION A.** It delivers real value (the Legal-Metrology base profile is the V1 compliance gate), stays bounded (defers the two multi-step sub-surfaces), and matches the "FieldSpec-driven, same convention as the catalog wizard" backend design intent (#11). **Until the founder rules, the build dispatch for this lane is BLOCKED** — the dashboard lane (lane 1) is unaffected and proceeds in parallel regardless.

> The rest of this spec (§3 onward) is written **assuming OPTION A**. If the founder picks B or C, the §3 build steps are revised accordingly before dispatch.

---

## 3. The build (ASSUMING OPTION A — base SellerProfile capture + edit)

### 3.0 `seller-profile.model.ts` (NEW — remote-private TS interfaces)
Transcribe §2.2/§2.3/§2.4/§2.5 field-for-field: `SellerProfile` (= `SellerProfileResponse`), `PatchProfileRequest`, `PatchActiveCategoriesRequest`, `RequiredFieldsResponse` + a `FieldSpec` interface read from the live shape (§2.5 caveat — do NOT invent keys). All remote-private (consumed by mfe-onboarding ONLY → no `@mesell/core` promotion; the 2+-remote criterion is not met, SP05 D32).

### 3.1 `SellerProfileService` (NEW — the extraction) — `services/seller-profile.service.ts`
`@Injectable()` route-scoped (provided in each component's `providers[]`, mirroring the dashboard/catalog-form pattern — NOT `providedIn:'root'`, this is remote-private state). Methods (via `ApiClient`, NO manual auth header — interceptor owns it):
- `getProfile(): Observable<SellerProfile>` → `GET /api/v1/seller-profile` (#7). 404 = no profile yet (first-time seller) → matrix maps to a "fresh profile" empty-shape, NOT an error.
- `getRequiredFields(): Observable<RequiredFieldsResponse>` → `GET /api/v1/seller-profile/required-fields` (#11).
- `patchProfile(body: PatchProfileRequest): Observable<SellerProfile>` → `PATCH /api/v1/seller-profile` (#8). Send ONLY the base fields the form collects (subset semantics — all optional).
- (DEFERRED to follow-up per Option A: `patchActiveCategories` #9, `patchCompliance` #10 — author the method stubs only if cheap, else omit and note.)
All with the §6 `catchError` matrix.

### 3.2 (component-builder) Onboarding form rebuild → real base profile
- Replace the `businessName/city/gstNumber` FormGroup with the **base SellerProfile** fields: `manufacturer_name`, `manufacturer_address`, `manufacturer_pincode` (validator `^\d{6}$`), `packer_name`, `packer_address`, `packer_pincode` (`^\d{6}$`), `country_of_origin` (default "India"). (Importer fields are nullable/optional — include only if `/required-fields` marks them required for the seller's scope; default-omit for V1 base.)
- On init: optionally call `getRequiredFields()` to drive which fields render + the `completed` map (FieldSpec convention). For Option A's bounded scope, a STATIC base-field form (the 6 mandatory LM fields + country) is acceptable if the FieldSpec renderer is judged too large — flag the choice. **Do NOT keep the GST validator** (no backend GST field); remove `optionalGstValidator` + `GST_PATTERN`.
- `onSubmit` → `patchProfile({...base fields})` → on success navigate `/dashboard`; render §6 states. Remove the `setTimeout` mock (L163-166).
- The `mee-steps` decorative indicator + `AuthLayoutComponent` wrapper stay.

### 3.3 (component-builder) Profile page → load + edit real base profile
- On init: `getProfile()` (#7) → `patchValue` the form from the response (NOT from `AuthService.currentUser().name` which does not exist on the wire). 404 → fresh/empty form.
- The identity card reads `AuthService.currentUser()` (`phone`, `plan` now available from Wave A; `name` is optional-legacy — keep the `|| 'Seller'` fallback). The plan badge can now use `currentUser()?.plan` instead of the hardcoded "Free plan" (optional polish; flag if done).
- The editable form: replace the display-`name` field with the same base SellerProfile fields as onboarding (or a subset). `onSubmit` → `patchProfile(...)`. Remove the `setTimeout` mock (L193-199).
- `onLogout` → `AuthService.logout()` + navigate `/login` (unchanged; the real `POST /auth/logout` is fired by the Wave-A `AuthApiService.logout()` path if profile calls it — confirm whether logout should hit the endpoint here; Wave A built `AuthApiService.logout()`. If profile should call it, that is consuming a Wave-A core service (allowed — read-only consumption), NOT editing core).

### 3.4 (ui-styler) error/offline states + screenshots
Tailwind + mee-* only; boundary 0. 360px+1280px of onboarding + profile in loading/error/data states.

---

## 4. Model promotion — none
All customer shapes are mfe-onboarding-private (single consumer). No `@mesell/core` promotion (SP05 D32 criterion not met). Do NOT promote.

## 5. (auth touch — consumption only)
Profile reads `AuthService.currentUser()`/`logout()` (Wave-A-frozen, read-only consumption — allowed). The C5 auth-singleton smoke (`auth-singleton.smoke.spec.ts`) must still pass — touch only annotations if the AuthUser-additive change surfaces; an ASSERTION rewrite = STOP (drift signal, §10).

---

## 6. Graceful-degradation matrix (VERBATIM from Wave A §6 — the canonical pattern)

> **R-W6-1 (P0). The merge gate REJECTS any wired service that removes its mock without this pattern.**

1. **Every `seller-profile.service.ts` method has a `catchError` matrix** mapping `HttpErrorResponse.status` → typed outcome:
   - **401** → `refreshInterceptor` retries; terminal 401 → `logout()` stands + return a fallback (fresh-profile shape for `getProfile`; re-throw-to-error-signal for patches). NEVER white-screen.
   - **402** (plan-guard) → customer module is plan_guard-EXCLUDED (router docstring) → unlikely; handle uniformly with a fallback.
   - **422** (validation — bad pincode `^\d{6}$`, or `extra="forbid"` rejection) → map the typed error envelope `{detail, code, validation_message_id, request_id, errors?[]}` to the offending field's inline error (the `validation_message_id` → user copy). **This is the field-validation path — surface it on the form, do NOT swallow.** (If a 422 fires for an UNEXPECTED key, that is the §2.6 mismatch resurfacing = STOP.)
   - **404** (`getProfile` — no profile row yet) → NOT an error; map to a fresh/empty profile (first-time seller). For patches, 404 should not occur (PATCH creates-on-first-write per schemas.py docstring).
   - **5xx** → contract-shaped fallback + `MeeAlertBanner` error state + retry. NEVER crash.
2. **Components render explicit `loading`/`error`/`empty`/`data` states** + `MeeAlertBanner`(error) / `MeeOfflineBanner`(offline) / field-level errors (422). NEVER an unhandled throw.
3. **`NetworkService.online`** gates `MeeOfflineBanner`.
4. **`ErrorService`** (interceptor-fed) for any global surface — non-blocking.

---

## 7. Branch plan (Model C — documented, NOT executed) + PARALLEL-LANE discipline

Same Model C as lane 1. The LEAD executes at step-2 dispatch (NOT the spec author, and NOT until §2.6 is ruled):

- **Integration branch:** `feature/wave6-onboarding/integration` cut from **POST-#135 develop** (re-fetch after #135). F3-protected (JSON-file body for `gh api PUT .../protection`).
- **Group branch:** `feature/wave6-onboarding/frontend` off integration.
- **Worktree:** `/tmp/mesell-wt/w6b-onb`. `pnpm install --config.dangerously-allow-all-builds=true` (or `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract`); `./node_modules/.bin/ng build mfe-onboarding` / `ng build frontend` directly.
- **Master tree:** NEVER branch-switch; `git branch <name> <start>` + push.
- **Founder-gate PR:** `feature/wave6-onboarding/integration` → `develop`, `[FOUNDER GATE — DO NOT MERGE]`, LEFT OPEN (D1). Lead gates + squashes the `frontend`→`integration` group PR.
- **5-day cap** (STOP/escalate).

### PARALLEL-LANE discipline (lane 2 ‖ lane 1 — FILE-DISJOINT)
- **This lane touches ONLY `apps/mfe-onboarding/**`.** Lane 1 touches ONLY `apps/mfe-dashboard/**`. ZERO overlap (different remotes). Both integration branches cut from the SAME post-#135 develop → union is conflict-free (SP02‖SP03 precedent).
- **Shared surfaces are FROZEN.** `@mesell/core` (any file), composites SOURCE, ANY remote `main.ts`, `apps/shell/**` → needing a change = STOP (§10). Consuming composites (`MeeAlertBanner`/`MeeOfflineBanner`/`AuthLayout`) is read-only and fine; both lanes consume composites without conflict (neither edits the barrel/source).

---

## 8. Builder sequence (SERIAL — mandatory) + dispatch headers

> **DO NOT dispatch until §2.6 is ruled.** Sequence below assumes Option A.

1. **`meesell-angular-service-builder` (session-1)** — `seller-profile.model.ts` (§3.0) + `SellerProfileService` (§3.1: #7/#8/#11, optional #9/#10 stubs) with the §6 matrix; `seller-profile.service.spec.ts` (`HttpTestingController`: #7 `GET /api/v1/seller-profile`, #8 `PATCH /api/v1/seller-profile` body=base subset, #11 `GET .../required-fields`; matrix tests 401/404→fresh/422→field-error/5xx). Re-confirm `apps/mfe-onboarding/**/*.spec.ts` discovery glob.
2. **`meesell-angular-component-builder` (session-2)** — rebuild onboarding form (§3.2) + profile load+edit (§3.3) to the real base-profile domain; remove GST validator + `setTimeout` mocks; render §6 states; update both component specs. The C5 smoke (`auth-singleton.smoke.spec.ts`) stays assertion-stable (STOP if an assertion rewrite is needed).
3. **`meesell-angular-ui-styler` (session-3)** — error/offline polish, 360/1280 screenshots. Tailwind + mee-* only; boundary 0.

### Dispatch header template
```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/apps/mfe-onboarding/. NO backend/ changes. NO @mesell/core / composites-source / main.ts / shell / mfe-dashboard changes (Wave-A FROZEN + parallel-lane disjoint).
SESSION: mesell-wave6-onboarding-frontend-session-{N}
TASK: <the §-slice above for this specialist>
CONTEXT: Wave 6 Wave B lane 2. ⛔ The as-built UI (businessName/city/GST/display-name) DOES NOT MATCH the backend (Legal-Metrology compliance fields) — FOUNDER RULED OPTION {A/B/C} per spec §2.6 (CONFIRM the ruling before building). Ground truth = spec_w6b_onboarding.md §2 (customer module file:line). Endpoints #7 GET /seller-profile, #8 PATCH /seller-profile (PatchProfileRequest base fields, pincode ^\d{6}$), #11 GET /seller-profile/required-fields (FieldSpec — read the live key set, do NOT invent). Branch feature/wave6-onboarding/frontend, worktree /tmp/mesell-wt/w6b-onb, cut from POST-#135 develop. Degradation matrix = §6. Consume Wave-A-frozen surfaces, do NOT modify them.
OUTPUT: <files + the §9 validation checklist evidence>
```

---

## 9. Validation checklist (step-3 merge gate, skeptical-lead, review worktree)

- **Builds GREEN ≤ 90 s (D12):** `ng build mfe-onboarding` AND `ng build frontend`. Record times. >90 s = STOP.
- **Full suite, NO drop:** baseline = post-#135 develop spec count (re-establish at dispatch). New `seller-profile.service.spec.ts` raises it MONOTONICALLY; edited component specs do not drop. DROP = silent discovery failure = HARD REJECT. `CI=true ng test frontend` 0 fail/0 skip. Re-confirm `apps/mfe-onboarding/**/*.spec.ts` discovery (4 specs: onboarding.component, profile.component, auth-singleton.smoke, seller-profile.service[NEW]).
- **Boundary grep = 0:** `grep -rn "from 'primeng" frontend/apps/mfe-onboarding --include=*.ts | grep -v libs/ui-kit/` → 0.
- **Singleton non-drift (P0, §6.G):** mfe-onboarding is THE original `@mesell/core` consumer (ProfileComponent → AuthService). Prove EXACTLY ONE `_mesell_core.js` chunk; AuthService DEFINITION only there (not inlined into a component chunk). The Wave-A interceptor import in main.ts keeps core shared — VERIFY this slice's new service does not inline core. The C5 smoke must pass.
- **Mock-removal grep:** `grep -rn "setTimeout" frontend/apps/mfe-onboarding/src/app/{onboarding,profile}.component.ts` → 0 (the inline mocks gone); `grep -rn "of(.*).pipe(.*delay" frontend/apps/mfe-onboarding` → 0.
- **Contract greps:** (a) wired URLs match §2.1 EXACTLY — `grep -rn "/api/v1/seller-profile" frontend/apps/mfe-onboarding` shows #7/#8/#11 (and #9/#10 if wired); (b) NO manual `Authorization`/`authHeaders`/`Bearer` (interceptor owns it); (c) `localStorage`/`sessionStorage` = 0; (d) NO `withCredentials` (not auth-cookie traffic); (e) `GST_PATTERN`/`optionalGstValidator`/`businessName`/`city`/`gstNumber` GONE (`grep` = 0 — the mock domain is removed); the pincode validator `^\d{6}$` PRESENT.
- **Degradation coverage (R-W6-1):** `catchError` matrix present in the service; components render `MeeAlertBanner`/`MeeOfflineBanner` + 422 field errors; specs assert error/404-fresh/422-field/offline paths. NO matrix = REJECT.
- **Parallel-lane disjointness:** `git diff --name-only <base>..HEAD` touches ONLY `apps/mfe-onboarding/**`. Any `@mesell/core`/composites-source/main.ts/shell/mfe-dashboard path = REJECT.
- **TS strict + strictTemplates ON:** `tsc` app + spec EXIT 0.
- **a11y + screenshots:** keyboard nav + aria on both forms; 360/1280 screenshots (loading/error/data) for onboarding + profile.
- **PR template fully filled**, bundle delta noted (near-zero shell-initial; remote-local).
- **Gate-4 note:** record whether the 5 customer endpoints have Gate-4 coverage. Don't block on Gate-4.

---

## 10. STOP conditions (escalate — do NOT paper over)

1. **§2.6 unresolved = STOP — do NOT dispatch.** The lane is BLOCKED on the founder's Option-A/B/C ruling. Dispatching against the mock domain produces a 422 storm.
2. **ANY `backend/` change needed = STOP** (cross-lead memo, not an edit).
3. **ANY shared-surface change** (`@mesell/core`, interceptors, composites SOURCE, any remote `main.ts`, `apps/shell/**`) = STOP.
4. **Contract drift BEYOND the documented set** — a NEW 422/4xx for an UNEXPECTED key (the §2.6 mismatch resurfacing) → STOP, backend memo, no client shim (R-W6-2).
5. **`FieldSpec` key set invented** instead of read from the live `/required-fields` shape / the i18n TypedDict = STOP (§2.5).
6. **Build > 90 s.** **TS strict disabled.** **Duplicated `@mesell/core` chunk** (P0).
7. **Any wired service without a `catchError` matrix** = auto-reject (R-W6-1).
8. **Diff touches a file outside `apps/mfe-onboarding/**`** = parallel-lane violation = reject.
9. **The C5 auth-singleton smoke needs an ASSERTION rewrite** (not just annotation) to pass with the additive AuthUser = drift signal = STOP.
10. **`feature/wave6-onboarding/frontend` open > 5 calendar days** unmerged.

---

## 11. Open ambiguities + ground-truth resolutions

| # | Ambiguity | Resolution (ground-truth) |
|---|---|---|
| B1 | MASTER PLAN §1.3 says onboarding wires #7/#8/#9/#10/#11 with "Reactive Forms already exist; wire submit → PATCH". | **PARTIALLY FALSE — the forms exist but collect the WRONG fields.** The as-built forms (`businessName/city/gstNumber`, display `name`) have ZERO overlap with the customer schema (Legal-Metrology). "Wire submit → PATCH" would 422 on `extra="forbid"`. This is a REBUILD, not a wire. → §2.6 founder ruling. The master plan's onboarding line is optimistic about the as-built state. |
| B2 | Which endpoints does V1 onboarding actually wire? | RESOLVED (Option A rec): #7 (get) + #8 (patch base) + #11 (required-fields, optional driver). DEFER #9 (active-categories picker) + #10 (per-super compliance wizard) to a follow-up — they are multi-step surfaces with their own UX, out of a single Wave-B lane's scope. Founder confirms at §2.6. |
| B3 | `AuthUser.name` read by profile — does it exist post-Wave-A? | RESOLVED: `name` is now OPTIONAL (Wave A additive-optional). The profile template `auth.currentUser()?.name \|\| 'Seller'` already uses `?.` + fallback → compiles + renders 'Seller' when undefined. The backend has NO profile display-name; do NOT wire a name to `PATCH /seller-profile` (no such field). The identity card stays a display-only read of the optional `name`/`phone`/`plan`. |
| B4 | `FieldSpec` TS shape for #11. | RESOLVED: read from the live `/required-fields` response or `app/i18n/schema_contract.py FieldSpec` TypedDict — do NOT invent (§2.5). If ambiguous at build time → backend memo (§12). |
| B5 | Is `SellerProfileService` root or route-scoped? | RESOLVED: route-scoped `@Injectable()` in each component's `providers[]` (mirrors dashboard/catalog-form; remote-private state; not a cross-remote singleton). NOT `providedIn:'root'`. |
| B6 | Does profile's logout call `POST /auth/logout`? | RESOLVED: Wave A built `AuthApiService.logout()` (core). Profile MAY consume it (read-only use of a core service = allowed) so logout clears the server refresh-cookie, not just the in-memory token. RECOMMEND yes; confirm the Wave-A `AuthApiService` surface at dispatch. Consuming it is NOT editing core. |
| B7 | Baseline spec count. | Re-establish at dispatch (post-#135). Do NOT hardcode 47. |
| B8 | 404 on `GET /seller-profile` for a first-time seller. | RESOLVED: 404 = no profile row yet (the row is created on first PATCH per schemas.py docstring). Matrix maps 404→fresh/empty profile, NOT an error banner. The onboarding flow is precisely the "no profile → create it" path. |

---

## 12. Cross-lead memos to open (lead, at dispatch — recorded, not yet filed)

- **→ founder / master (STATUS_MASTER blocker, BEFORE dispatch):** §2.6 P0 mismatch — the as-built onboarding/profile UI domain (businessName/city/GST/display-name) does not exist in the backend customer module (Legal-Metrology fields). The lane needs an Option A/B/C ruling before the build dispatch. Recommend Option A (rebuild to base SellerProfile, defer #9/#10). The dashboard lane is unaffected and proceeds in parallel. **This is the gating blocker for lane 2.**
- **→ backend (`meesell-backend-coordinator`):** (1) confirm the `RequiredFieldsResponse.base_fields` FieldSpec key set (the live shape of `app/i18n/schema_contract.py FieldSpec`) so the FE TS interface is field-accurate (B4); (2) confirm the 5 customer endpoints' Gate-4 coverage for the PR two-sided-proof note. INFORMATIONAL + one contract-clarification.
- **→ ai (`meesell-ai-coordinator`):** NONE (no AI affordance on onboarding/profile).
