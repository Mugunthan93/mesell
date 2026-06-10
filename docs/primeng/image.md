# Image

**Import:** `import { Image } from 'primeng/image'`
**Selector:** `p-image`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| src | `string \| SafeUrl` | undefined | Source path for the image |
| srcSet | `string \| SafeUrl` | undefined | srcset definition |
| sizes | `string \| undefined` | undefined | sizes definition for responsive images |
| previewImageSrc | `string \| SafeUrl` | undefined | Source for a different preview (zoom) image |
| alt | `string \| undefined` | undefined | Alt text |
| width | `string \| undefined` | undefined | Width attribute |
| height | `string \| undefined` | undefined | Height attribute |
| preview | `boolean` | false | Enable click-to-preview/zoom |
| imageClass | `string \| undefined` | undefined | CSS class for the image element |
| imageStyle | `object \| null` | undefined | Inline style for the image element |
| styleClass | `string \| undefined` | undefined | **Deprecated v20.** Use `class` instead |
| placeholder | `string` | undefined | Placeholder image shown while loading |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when preview is shown |
| onHide | `EventEmitter<any>` | Emitted when preview is hidden |
| onImageError | `EventEmitter<Event>` | Emitted on image load error |

## Usage Example (from Sakai-ng)

```html
<!-- Basic image -->
<p-image src="https://example.com/product.jpg" alt="Product" width="250" />

<!-- Image with preview/zoom enabled -->
<p-image
  src="https://example.com/product.jpg"
  alt="Product"
  width="300"
  [preview]="true"
/>
```

## Notes

- `[preview]="true"` adds a magnifier overlay — clicking opens a lightbox.
- For simple img tags without preview, use native `<img>` directly.
