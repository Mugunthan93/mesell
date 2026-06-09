# Avatar

**Import:** `import { Avatar } from 'primeng/avatar'`
**Selector:** `p-avatar`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | `string \| undefined` | undefined | Defines the text to display |
| icon | `string \| undefined` | undefined | Defines the icon to display (PrimeIcons class) |
| image | `string \| undefined` | undefined | Defines the image URL to display |
| size | `'normal' \| 'large' \| 'xlarge' \| undefined` | `'normal'` | Size of the element |
| shape | `'square' \| 'circle' \| undefined` | `'square'` | Shape of the element |
| styleClass | `string \| undefined` | undefined | **Deprecated v20.** Use `class` attribute instead |
| ariaLabel | `string \| undefined` | undefined | ARIA label string |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby element IDs |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onImageError | `EventEmitter<Event>` | Triggered if an error occurs loading the image |

## Usage Example (from Sakai-ng)

```html
<!-- Image avatar, large circle -->
<p-avatar image="https://example.com/user.png" size="large" shape="circle"></p-avatar>

<!-- Label avatar -->
<p-avatar label="JD" shape="circle"></p-avatar>

<!-- Icon avatar -->
<p-avatar icon="pi pi-user" shape="circle"></p-avatar>
```

## Notes

- Use `p-avatargroup` as a wrapper to stack multiple avatars.
- `shape="circle"` is common for user profile avatars.
- `onImageError` is useful for fallback to label/icon when image fails to load.
