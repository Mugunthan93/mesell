# Panel

**Import:** `import { Panel } from 'primeng/panel'`
**Selector:** `p-panel`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| header | `string \| undefined` | undefined | Header text |
| toggleable | `boolean` | false | Allow collapsing via the header |
| collapsed | `boolean` | false | Initial collapsed state |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| collapsedChange | `EventEmitter<boolean>` | Emitted on collapse/expand change |
| onBeforeToggle | `EventEmitter<PanelBeforeToggleEvent>` | Emitted before toggle |
| onAfterToggle | `EventEmitter<PanelAfterToggleEvent>` | Emitted after toggle |

## Usage Example (from Sakai-ng)

```html
<p-panel header="Header" [toggleable]="true">
  <p>Content inside the panel.</p>
</p-panel>
```

## Notes

- Similar to `p-fieldset` but uses a card-like container style.
- Use `[(collapsed)]` for two-way binding.
- Custom header/footer via `pTemplate="header"` and `pTemplate="footer"` slots.
