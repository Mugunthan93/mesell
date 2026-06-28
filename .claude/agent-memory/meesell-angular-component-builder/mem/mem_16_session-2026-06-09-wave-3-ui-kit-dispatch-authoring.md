## Session 2026-06-09 — Wave 3 UI Kit Dispatch Authoring {#wave-3-dispatch-authoring}

### Task
Authored `/Users/mugunthansrinivasan/Project/mesell/docs/ui_ux/WAVE_3_UI_KIT_DISPATCH.md` — the spec document for all 17 mee-* primitives in `src/app/ui/`.

### Key findings from source reads

#### PrimeNG 21 — directive vs component trap
- `InputText` = DIRECTIVE → `<input pInputText>` NOT `<p-inputtext>`
- `Textarea` = DIRECTIVE → `<textarea pTextarea>` NOT `<p-textarea>`
- `p-select` replaces `p-dropdown` (same CVA API, new selector)
- `mee-badge` wraps `p-tag` (label chip) NOT `p-badge` (numeric overlay)
- `p-steps` uses `model: MenuItem[]` — the `mee-steps` wrapper must convert `MeeStep[]` to `MenuItem[]`

#### CVA assignment (from architecture doc)
- CVA YES: mee-input (K2), mee-otp-input (K3), mee-select (K10), mee-password-input (K16), mee-textarea (K17)
- CVA NO: mee-tree-select (K11) — architecture specifies `value_change` output only, no CVA

#### Contract ambiguity found in architecture doc
Three ambiguities exist in `FRONTEND_ARCHITECTURE.md §Layer 2` that required judgment calls:
1. `mee-card` (K5): architecture lists "content via <ng-content>" only — no explicit @Input list. Doc says just project content. Treated as zero @Inputs.
2. `mee-password-input` (K16): architecture lists "CVA, toggle mask" but does NOT list individual @Inputs. Inferred from `docs/primeng/password.md`: `placeholder`, `disabled`, `toggleMask`, `feedback`. This is the most significant gap.
3. `mee-textarea` (K17): architecture lists "label, error, CVA" but no full @Input list. Mirrored mee-input pattern (label, placeholder, rows, error, hint, disabled, required, autoResize) to be consistent.

#### Service-based primitives
- K14 `mee-toast`: host component + `MeeToastService` (wraps `MessageService`) — `providedIn: 'root'`
- K15 `mee-confirm-dialog`: host component + `MeeConfirmService` (wraps `ConfirmationService`) — `providedIn: 'root'`
- `MessageService` + `ConfirmationService` from `primeng/api` must be in `app.config.ts` providers

#### Build status at time of authoring
- `src/app/ui/` does NOT exist (confirmed via `ls` check)
- Layer 1 `_tokens.css` exists (confirmed by coordinator status entry)
- Wave 2B scaffold DONE (Gates 1-4 PASS per STATUS_FRONTEND.md)

### Dispatch output
- File: `/Users/mugunthansrinivasan/Project/mesell/docs/ui_ux/WAVE_3_UI_KIT_DISPATCH.md`
- 17 primitives covered, 48 files specified in tree
- Build priority order: button → input → otp-input → badge → card → table → dialog → file-upload → steps → select → tree-select → skeleton → progress-bar → toast → confirm-dialog → password-input → textarea
- Five verification gates defined (Gate 5 optional kitchen-sink demo)

---
