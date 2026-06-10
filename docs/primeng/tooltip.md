# Tooltip

**Import:** `import { Tooltip } from 'primeng/tooltip'`
**Selector:** `[pTooltip]` (DIRECTIVE on any host element)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> `Tooltip` is a DIRECTIVE — apply it as an attribute on any HTML element or component. There is no `<p-tooltip>` component tag.

## Directive Inputs

| Prop | Attribute alias | Type | Default | Description |
|------|----------------|------|---------|-------------|
| content | `pTooltip` | `string \| TemplateRef` | undefined | Tooltip text or template |
| disabled | `tooltipDisabled` | `boolean` | false | Disable the tooltip |
| tooltipPosition | `tooltipPosition` | `'right'\|'left'\|'top'\|'bottom'` | `'right'` | Placement |
| tooltipEvent | `tooltipEvent` | `'hover'\|'focus'\|'both'` | `'hover'` | Trigger event |
| showDelay | `showDelay` | `number` | undefined | Delay before showing (ms) |
| hideDelay | `hideDelay` | `number` | undefined | Delay before hiding (ms) |
| life | `life` | `number` | undefined | Auto-hide after N ms (0 = stays until hover out) |
| positionTop | `positionTop` | `number` | undefined | Vertical offset adjustment |
| positionLeft | `positionLeft` | `number` | undefined | Horizontal offset adjustment |
| escape | `escape` | `boolean` | true | Escape HTML in tooltip content |
| autoHide | `autoHide` | `boolean` | true | Hide when mouse leaves tooltip area |
| tooltipStyleClass | `tooltipStyleClass` | `string` | undefined | CSS class for tooltip overlay |
| appendTo | (signal) | `any` | undefined | Target for overlay attachment |

## Usage Example

```html
<!-- Basic tooltip -->
<p-button label="Save" pTooltip="Save current changes" tooltipPosition="top" />

<!-- On an icon -->
<i class="pi pi-info-circle" pTooltip="This field is required" tooltipPosition="right"></i>

<!-- Show on focus (accessibility) -->
<input pInputText pTooltip="Enter your 10-digit phone number" tooltipEvent="focus" />

<!-- Disabled tooltip -->
<p-button label="Export" [pTooltip]="exportTooltip" [tooltipDisabled]="!hasData()" />

<!-- With delay -->
<p-button label="Delete" pTooltip="This action cannot be undone" [showDelay]="500" tooltipPosition="bottom" />
```

## Notes

- Add `Tooltip` to the component's `imports` array (standalone).
- Tooltip text is set directly via `[pTooltip]="'text'"` or `pTooltip="text"` (static).
- For icon-only buttons always add `pTooltip` for accessibility.
- `tooltipEvent="focus"` is important for keyboard-accessible tooltips on form inputs.
