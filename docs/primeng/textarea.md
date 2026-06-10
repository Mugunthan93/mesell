# Textarea

**Import:** `import { Textarea } from 'primeng/textarea'`
**Selector:** `[pTextarea]`, `[pInputTextarea]` (DIRECTIVE on native `<textarea>`)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> `Textarea` is a DIRECTIVE applied to a native `<textarea>` element — not a standalone component. Do NOT write `<p-textarea>`.

## @Input() Props (as directive attributes)

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| autoResize | `boolean` | false | Auto-grow height as content increases |
| pSize | `string \| undefined` | undefined | `'small'` or `'large'` size variant |
| variant | (signal) `'filled' \| 'outlined'` | undefined | Visual fill variant |
| fluid | (signal) `boolean` | false | Full-width textarea |
| invalid | (signal) `boolean` | false | Apply invalid/error styling |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onResize | `EventEmitter<Event>` | Emitted when auto-resize occurs |

## Usage Example

```html
<!-- Basic pTextarea -->
<textarea pTextarea rows="4" cols="30" placeholder="Product description" class="w-full"></textarea>

<!-- With auto-resize -->
<textarea pTextarea [autoResize]="true" rows="3" class="w-full"></textarea>

<!-- With reactive form -->
<textarea pTextarea formControlName="description" rows="5" [variant]="'filled'" class="w-full"></textarea>

<!-- With float label -->
<p-floatlabel variant="on">
  <textarea pTextarea id="desc" formControlName="description" rows="4" class="w-full"></textarea>
  <label for="desc">Description</label>
</p-floatlabel>

<!-- With invalid state -->
<textarea pTextarea [invalid]="form.get('description')?.invalid && form.get('description')?.touched"></textarea>
```

## Notes

- DIRECTIVE on native `<textarea>` — apply as attribute, not component selector.
- The native `rows`, `cols`, `placeholder`, `disabled`, `maxlength` attributes work as normal.
- `autoResize` eliminates the need for a fixed row count — grows with content.
- Use `[fluid]="true"` or Tailwind `w-full class="w-full"` for full-width layout.
- Works natively with `formControlName` (Reactive Forms) and `[(ngModel)]`.
