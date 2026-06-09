# ButtonGroup

**Import:** `import { ButtonGroup } from 'primeng/buttongroup'`
**Selector:** `p-buttongroup`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

None (structural wrapper only).

## @Output() Events

None.

## Usage Example

```html
<!-- Group of related buttons without gaps -->
<p-buttongroup>
  <p-button label="Save" icon="pi pi-check" severity="primary"></p-button>
  <p-button label="Delete" icon="pi pi-trash" severity="danger"></p-button>
  <p-button label="Cancel" [outlined]="true"></p-button>
</p-buttongroup>
```

## Notes

- `ButtonGroup` is a layout container that removes the visual gaps between adjacent buttons.
- Import `ButtonGroup` from `'primeng/buttongroup'` and `Button` from `'primeng/button'` together.
