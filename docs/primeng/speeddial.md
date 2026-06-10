# SpeedDial

**Import:** `import { SpeedDial } from 'primeng/speeddial'`
**Selector:** `p-speeddial`, `p-speedDial`, `p-speed-dial`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[] \| null` | undefined | Array of menu items |
| visible | `boolean` | false | Controls open/closed state |
| direction | `'up'\|'down'\|'left'\|'right'\|'up-left'\|'up-right'\|'down-left'\|'down-right'` | `'up'` | Direction of action expansion |
| type | `'linear'\|'circle'\|'semi-circle'\|'quarter-circle'` | `'linear'` | Opening layout type |
| radius | `number` | 0 | Radius for circle/semi-circle/quarter-circle types |
| mask | `boolean` | false | Show backdrop mask |
| maskStyle | `object` | undefined | Inline style for mask element |
| maskClassName | `string \| undefined` | undefined | CSS class for mask element |
| showIcon | `string \| undefined` | undefined | Icon class for the trigger button (open state) |
| hideIcon | `string \| undefined` | undefined | Icon class for the trigger button (close state) |
| rotateAnimation | `boolean` | true | Rotate icon when no hideIcon defined |
| disabled | `boolean` | false | Disables all actions |
| transitionDelay | `number` | 30 | Delay between each action item animation (ms) |
| tooltipPosition | `'bottom'\|'top'\|'left'\|'right'` | `'bottom'` | Tooltip position for actions |
| buttonProps | `ButtonProps` | — | Props forwarded to the trigger button |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onVisibleChange | `EventEmitter<boolean>` | Emitted when visibility changes |
| onClick | `EventEmitter<SpeedDialClickEvent>` | Emitted when trigger button clicked |
| onShow | `EventEmitter<any>` | Emitted when actions open |
| onHide | `EventEmitter<any>` | Emitted when actions close |

## Usage Example

```html
<!-- Basic speed dial (expands up) -->
<p-speeddial
  [model]="actionItems"
  direction="up"
  [style]="{ position: 'fixed', bottom: '1rem', right: '1rem' }"
/>

<!-- In component -->
actionItems: MenuItem[] = [
  { icon: 'pi pi-pencil', command: () => this.edit() },
  { icon: 'pi pi-trash', command: () => this.delete() },
  { icon: 'pi pi-share-alt', command: () => this.share() }
];
```

## Notes

- `model` items use the standard `MenuItem` interface from `primeng/api`.
- Position the SpeedDial with Tailwind `fixed`/`absolute` + corner utilities.
- For controlled visibility, use `[(visible)]="dialOpen"`.
