# Galleria

**Import:** `import { Galleria } from 'primeng/galleria'`
**Selector:** `p-galleria`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `any[]` | undefined | Array of image objects |
| activeIndex | `number` | 0 | Index of the currently displayed item |
| numVisible | `number` | 3 | Number of thumbnail items visible |
| responsiveOptions | `GalleriaResponsiveOptions[]` | undefined | Responsive breakpoint options |
| fullScreen | `boolean` | false | Display in fullscreen mode |
| showItemNavigators | `boolean` | false | Show previous/next nav buttons |
| showThumbnailNavigators | `boolean` | true | Show thumbnail nav buttons |
| showItemNavigatorsOnHover | `boolean` | false | Show nav buttons only on hover |
| showIndicators | `boolean` | false | Show slide indicators |
| showThumbnails | `boolean` | true | Show thumbnail strip |
| circular | `boolean` | false | Infinite loop scrolling |
| autoPlay | `boolean` | false | Auto-advance slideshow |
| transitionInterval | `number` | 4000 | Auto-play interval in ms |
| style | `object \| null` | undefined | Inline style |
| containerStyle | `object \| null` | undefined | Container inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| activeIndexChange | `EventEmitter<number>` | Emitted when active item changes |
| visibleChange | `EventEmitter<boolean>` | Emitted when fullscreen visibility changes |

## Usage Example (from Sakai-ng)

```html
<p-galleria
  [value]="images()"
  [responsiveOptions]="galleriaResponsiveOptions"
  [containerStyle]="{ 'max-width': '640px' }"
  [numVisible]="5"
>
  <ng-template pTemplate="item" let-item>
    <img [src]="item.itemImageSrc" [alt]="item.alt" style="width: 100%; display: block;" />
  </ng-template>
  <ng-template pTemplate="thumbnail" let-item>
    <img [src]="item.thumbnailImageSrc" [alt]="item.alt" />
  </ng-template>
</p-galleria>
```

## Notes

- Use `pTemplate="item"` for the main image and `pTemplate="thumbnail"` for thumbnails.
- `autoPlay` requires `circular="true"` to work properly.
