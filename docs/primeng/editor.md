# Editor

**Import:** `import { Editor } from 'primeng/editor'`
**Selector:** `p-editor`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `string \| undefined` | undefined | HTML value (two-way via `[(ngModel)]`) |
| placeholder | `string \| undefined` | undefined | Placeholder text |
| formats | `string[] \| undefined` | undefined | Whitelist of Quill formats |
| modules | `object \| undefined` | undefined | Quill module configuration |
| bounds | `string \| HTMLElement` | `'body'` | Boundary for the editor |
| scrollingContainer | `string \| HTMLElement \| null` | null | Scrolling container |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |
| readonly | `boolean` | false | Read-only mode |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onTextChange | `EventEmitter<EditorTextChangeEvent>` | Emitted when text changes |
| onSelectionChange | `EventEmitter<EditorSelectionChangeEvent>` | Emitted when selection changes |
| onInit | `EventEmitter<EditorInitEvent>` | Emitted when editor is initialized |

## Usage Example

```html
<p-editor [(ngModel)]="htmlContent" [style]="{ height: '320px' }"></p-editor>

<!-- Reactive form -->
<p-editor formControlName="description" [style]="{ height: '250px' }"></p-editor>
```

## Notes

- Built on top of **Quill** editor. Quill must be installed: `npm install quill`.
- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- The value is an HTML string.
- For plain-text-only use, prefer `p-textarea`.
