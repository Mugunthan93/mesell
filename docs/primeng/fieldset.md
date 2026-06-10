# Fieldset

**Import:** `import { Fieldset } from 'primeng/fieldset'`
**Selector:** `p-fieldset`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| legend | `string \| undefined` | undefined | Header/legend text |
| toggleable | `boolean \| undefined` | false | Content can be toggled by clicking the legend |
| collapsed | `boolean` | false | Initial collapsed state (use with `toggleable`) |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| collapsedChange | `EventEmitter<boolean>` | Emitted on collapse/expand state change |
| onBeforeToggle | `EventEmitter<FieldsetBeforeToggleEvent>` | Emitted before toggle |
| onAfterToggle | `EventEmitter<FieldsetAfterToggleEvent>` | Emitted after toggle |

## Usage Example (from Sakai-ng)

```html
<p-fieldset legend="Legend" [toggleable]="true">
  <p>Content inside the fieldset.</p>
</p-fieldset>
```

## Notes

- Similar to HTML `<fieldset>` but with PrimeNG styling and optional collapse.
- Use `[(collapsed)]` for two-way collapse binding.
