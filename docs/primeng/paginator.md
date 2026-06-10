# Paginator

**Import:** `import { Paginator } from 'primeng/paginator'`
**Selector:** `p-paginator`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| totalRecords | `number` | undefined | Total number of records |
| rows | `number` | undefined | Number of rows per page |
| first | `number` | 0 | Index of the first record on the current page |
| rowsPerPageOptions | `any[]` | undefined | Options for rows-per-page dropdown (e.g. `[10, 25, 50]`) |
| pageLinkSize | `number` | 5 | Number of page link buttons |
| alwaysShow | `boolean` | true | Show paginator even with single page |
| showCurrentPageReport | `boolean \| undefined` | undefined | Show `{currentPage} of {totalPages}` text |
| currentPageReportTemplate | `string` | `'{currentPage} of {totalPages}'` | Template for page report text |
| showFirstLastIcon | `boolean` | — | Show first/last page buttons |
| showJumpToPageDropdown | `boolean` | — | Show page jump dropdown |
| showPageLinks | `boolean` | — | Show individual page link buttons |
| styleClass | `string \| undefined` | undefined | CSS class |
| locale | `string \| undefined` | undefined | Locale for number formatting |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onPageChange | `EventEmitter<PaginatorState>` | Emitted when page or rows changes |

## Key Interfaces

```typescript
interface PaginatorState {
  first: number;     // Index of first record on new page
  rows: number;      // Rows per page
  page: number;      // Current page index (0-based)
  pageCount: number; // Total number of pages
}
```

## Usage Example

```html
<p-paginator
  [rows]="10"
  [totalRecords]="120"
  [rowsPerPageOptions]="[10, 20, 50]"
  (onPageChange)="onPageChange($event)"
></p-paginator>
```

## Notes

- Used standalone or in conjunction with `p-table` (which has a built-in paginator).
- `first` prop allows external control of the current page position.
- `rows` changes are also emitted in `onPageChange` when using `rowsPerPageOptions`.
