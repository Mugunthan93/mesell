# AvatarGroup

**Import:** `import { AvatarGroup } from 'primeng/avatargroup'`
**Selector:** `p-avatargroup`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| styleClass | `string \| undefined` | undefined | **Deprecated v20.** Use `class` attribute instead |
| style | `object \| null` | undefined | Inline style |

## @Output() Events

None.

## Usage Example (from Sakai-ng)

```html
<p-avatargroup styleClass="mb-4">
  <p-avatar image="https://example.com/user1.png" size="large" shape="circle"></p-avatar>
  <p-avatar image="https://example.com/user2.png" size="large" shape="circle"></p-avatar>
  <p-avatar image="https://example.com/user3.png" size="large" shape="circle"></p-avatar>
  <p-avatar label="+3" shape="circle" size="large"></p-avatar>
</p-avatargroup>
```

## Notes

- Used as a container for multiple `p-avatar` elements to display them overlapping.
- Import both `AvatarGroup` and `Avatar` from their respective modules.
