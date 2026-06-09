# ColorPicker

**Import:** `import { ColorPicker } from 'primeng/colorpicker'`
**Selector:** `p-colorPicker`, `p-colorpicker`, `p-color-picker`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| format | `'hex' \| 'rgb' \| 'hsb'` | `'hex'` | Format for the value binding |
| inline | `boolean \| undefined` | undefined | Display as inline panel (not overlay) |
| inputId | `string \| undefined` | undefined | ID of the input element |
| tabindex | `string \| undefined` | undefined | Tab index |
| disabled | `boolean` | false | Disables the component |
| styleClass | `string \| undefined` | undefined | CSS class |
| autoZIndex | `boolean` | true | Automatically manage z-index |
| baseZIndex | `number` | 0 | Base z-index |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<ColorPickerChangeEvent>` | Emitted on color change |
| onShow | `EventEmitter<any>` | Emitted when overlay shows |
| onHide | `EventEmitter<any>` | Emitted when overlay hides |

## Usage Example (from Sakai-ng)

```html
<!-- Inline color picker bound to a model -->
<p-colorpicker [style]="{ width: '2rem' }" [(ngModel)]="colorValue"></p-colorpicker>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- `format="hex"` returns `"#RRGGBB"` strings.
- `format="rgb"` returns `{ r: number, g: number, b: number }` objects.
- `inline="true"` shows the picker permanently without a trigger swatch.
