# Splitter

**Import:** `import { Splitter, SplitterPanel } from 'primeng/splitter'`
**Selector:** `p-splitter` (container), `p-splitter-panel` (panel slot)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## Splitter @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| layout | `'horizontal' \| 'vertical'` | `'horizontal'` | Panel arrangement direction |
| gutterSize | `number` | 4 | Width/height of the resize gutter in pixels |
| panelSizes | `number[]` | undefined | Initial panel sizes as percentages (e.g., `[30, 70]`) |
| minSizes | `number[]` | undefined | Minimum sizes per panel as percentages |
| stateKey | `string \| undefined` | undefined | Key for persisting state |
| stateStorage | `'local' \| 'session'` | `'session'` | Storage type for persistence |
| panelStyle | `object` | undefined | Inline style for panel elements |
| panelStyleClass | `string \| undefined` | undefined | CSS class for panel elements |
| step | `number` | 5 | Keyboard increment step (px) |

## Splitter @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onResizeEnd | `EventEmitter<SplitterResizeEndEvent>` | Emitted when resize gesture ends |
| onResizeStart | `EventEmitter<SplitterResizeStartEvent>` | Emitted when resize gesture starts |

## Usage Example

```html
<!-- Horizontal split (default) -->
<p-splitter [panelSizes]="[30, 70]" [gutterSize]="8" styleClass="h-96">
  <ng-template pTemplate="panel">
    <div class="p-4 overflow-auto h-full">Left panel</div>
  </ng-template>
  <ng-template pTemplate="panel">
    <div class="p-4 overflow-auto h-full">Right panel</div>
  </ng-template>
</p-splitter>

<!-- Vertical split -->
<p-splitter layout="vertical" [panelSizes]="[40, 60]" styleClass="h-screen">
  <ng-template pTemplate="panel">Top</ng-template>
  <ng-template pTemplate="panel">Bottom</ng-template>
</p-splitter>
```

## Notes

- Each panel is declared as a `pTemplate="panel"` inside `<p-splitter>`.
- `panelSizes` values must add up to 100 (percentages).
- Use `stateKey` to persist the user's panel size preference in localStorage/sessionStorage.
