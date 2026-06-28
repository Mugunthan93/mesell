## Session 2026-06-07 — Wave 3 — images feature {#images-wave-3}

### Route touched
`/catalogs/:id/images` — features/images/

### Services consumed
`ImagesApiService` (own, replaced stub this dispatch) + `NgxImageCompressService` + `MatDialog` + `MatSnackBar` + `ActivatedRoute` + `Router`

### Pattern: ApiClient.postMultipart returns Observable<T>, NOT Observable<HttpEvent<T>>
- The existing ApiClient.postMultipart uses `http.post<T>()` WITHOUT `{ reportProgress: true, observe: 'events' }`.
- It returns `Observable<T>` (just the response body), NOT an HttpEvent stream.
- Upload progress % (0–100) is therefore NOT available via this method.
- Consequence: uploading state tracks as a boolean flag (uploading[slotIndex]=true/false), not as a %.
- Future upgrade: if upload progress is needed, ApiClient would need a new method using
  `http.request(new HttpRequest('POST', url, formData, { reportProgress: true }))`.
- This is a DEVIATION from the task spec which requested `Observable<HttpEvent<T>>`.

### Pattern: ProductImage model uses snake_case (API wire format)
- The existing stub used camelCase (slotIndex, precheckResults, isJpeg, colorSpaceOk...).
- The actual API contract uses snake_case: slot_index, precheck_jsonb, gcs_url, is_jpeg,
  color_space, resolution_ok, white_bg_ok, watermark_pass.
- ALWAYS use the API spec's snake_case shape for feature-local models. The stub was wrong.

### Pattern: Export pure functions from components to avoid NG0950 in specs
- Components with `input.required()` signals: calling the signal in a computed()
  throws NG0950 in vitest+jsdom if the input hasn't been set.
- Solution: extract computation logic into a standalone exported PURE FUNCTION.
  e.g., `export function buildPrecheckItems(image: ProductImage): PrecheckItem[]`
         `export function imageStatusBadgeClass(status: ...): string`
- Test the pure function directly in specs — no TestBed component needed for logic tests.
- The component's `computed()` delegates to the pure function:
  `readonly precheckItems = computed(() => buildPrecheckItems(this.image()));`
- This avoids the NG0950 trap entirely for the 2 logic-heavy test cases.

### Pattern: overrideComponent remove[] must list real component classes
- `remove: { imports: [RealChild] }` (explicitly listing the class) works correctly.
- `remove: { imports: [] }` (empty array) does NOT remove anything — NG0300 results.
- Always check: when using ImageSlotComponent + PrecheckReportComponent inside a parent,
  explicitly list both in the remove[] array of overrideComponent.

### Pattern: Polling with destroy$ Subject (OnDestroy)
- Use `private readonly destroy$ = new Subject<void>()` for simple observable lifecycle.
- `pollImages().pipe(takeUntil(this.destroy$)).subscribe(...)` — terminates on destroy.
- `ngOnDestroy(): void { this.destroy$.next(); this.destroy$.complete(); }`
- Re-start polling by calling `this.startPolling(id)` again after upload completes.
- This is the pattern for components that do NOT use `takeUntilDestroyed()` from rxjs-interop
  (which requires injection context — constructor or injector-provided destroyRef).
- `takeUntilDestroyed()` in ngOnInit is fine IF DestroyRef is injected explicitly.

### Pattern: MatDialog.open + ConfirmDialogComponent (input() signals, not MAT_DIALOG_DATA)
- ConfirmDialogComponent uses `input<T>(default)` signals (NOT MAT_DIALOG_DATA injection).
- Set inputs via `dialogRef.componentRef!.setInput('inputName', value)` AFTER open().
- Use `!` non-null assertion (componentRef is defined when dialog is open).
- `dialogRef.afterClosed().subscribe((confirmed: boolean) => { ... })` for result.
- This is the CORRECT pattern for Material dialogs using the new Angular input() API.

### Pattern: ngx-image-compress compressFile usage
- `NgxImageCompressService.compressFile(dataUrl, orientation, ratio, quality): Promise<string>`
- orientation: -2 = auto-detect from EXIF
- ratio: 75 = reduce to 75% of original pixel dimensions
- quality: 75 = 75% JPEG quality
- Must read file as dataUrl first (FileReader + readAsDataURL).
- Convert compressed dataUrl back to Blob: split on ',', atob(base64), Uint8Array, new Blob([]).
- Inject NgxImageCompressService in the component's own `providers: []` array (it is
  NOT providedIn: 'root') OR ensure it's provided at a parent level. For standalone
  page components, add `providers: [NgxImageCompressService]` in @Component decorator.

### Pattern: canProceed computed gate (images → preview)
- `canProceed = computed(() => slot0?.status === 'ready' && slot0.precheck_jsonb?.watermark_pass === true)`
- Slot 0 (front image) must be 'ready' AND watermark_pass must be exactly `true` (not null, not undefined).
- "Next step" button `[disabled]="!canProceed()"` prevents navigation until gate passes.

### Build result (2026-06-07 Wave 3 images)
- images-component lazy chunk: 30.90 kB raw / 8.38 kB gzip (budget ≤80 kB — 89% headroom)
- 12/12 new tests passing (4 spec files)
- Total suite: 241/254 passing; 13 pre-existing failures unchanged
- ng build --configuration=production: ZERO errors, 1 new NG8102 warning (benign)


---
