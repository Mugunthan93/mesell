# PrimeNG 21 Component Reference — Master Index

**Version:** PrimeNG 21.1.9 (Angular 21)
**Generated from:** `frontend/node_modules/primeng/types/primeng-*.d.ts`
**Cross-referenced:** `themes/sakai-ng/src/app/pages/uikit/`

This index is the **canonical import/selector/API truth** for all meesell-* agents. Read the individual `.md` before using any PrimeNG component.

---

## Critical v21 Breaking Changes

| Change | Impact |
|--------|--------|
| `SidebarModule` / `p-sidebar` REMOVED | Use `Drawer` (`p-drawer`) instead |
| `p-message` `text` prop deprecated | Use content projection: `<p-message>text</p-message>` |
| `p-dropdown` deprecated | Use `p-select` (same API, new selector) |
| `p-inputNumber` → `p-inputnumber` (alias available) | New canonical selector |
| `p-tabView` / `p-accordionTab` deprecated | Use composable `p-tabs` / `p-accordion` APIs |
| `showTransitionOptions` / `hideTransitionOptions` deprecated | Use `motionOptions` (signal) |
| `styleClass` deprecated on many components | Use `class` attribute directly |

---

## Wave Usage Map (MeeSell V1 Routes)

### Wave 2C — Core Auth + UI Primitives

| Route | Component | PrimeNG used |
|-------|-----------|-------------|
| `/signup` | `SignupComponent` | `inputtext`, `inputotp`, `button`, `message`, `floatlabel`, `iconfield`, `inputicon` |
| `/login` | `LoginComponent` | `inputtext`, `inputotp`, `button`, `message`, `floatlabel`, `iconfield`, `inputicon` |
| `/` | `LandingComponent` | `button`, `card`, `tag`, `divider` |

### Wave 3 — Dashboard

| Route | Component | PrimeNG used |
|-------|-----------|-------------|
| `/dashboard` | `DashboardComponent` | `table`, `select`, `iconfield`, `inputicon`, `inputtext`, `button`, `tag`, `skeleton`, `badge`, `paginator`, `toolbar` |

### Wave 4 — Catalog Flow

| Route | Component | PrimeNG used |
|-------|-----------|-------------|
| `/catalogs/new` | `SmartPickerComponent` | `card`, `button`, `skeleton`, `badge`, `inputtext`, `iconfield` |
| `/catalogs/:id/edit` | `CatalogFormComponent` | `inputtext`, `textarea`, `select`, `inputnumber`, `floatlabel`, `button`, `accordion`, `panel`, `message`, `skeleton`, `togglebutton` |
| `/catalogs/:id/images` | `ImageUploaderComponent` | `fileupload`, `progressbar`, `image`, `button`, `message`, `tag`, `dialog`, `panel` |
| `/catalogs/:id/preview` | `PreviewComponent` | `tabs`, `card`, `image`, `tag`, `divider`, `button`, `skeleton`, `panel` |
| `/catalogs/:id/pricing` | `PricingComponent` | `slider`, `inputnumber`, `button`, `divider`, `card`, `panel`, `tag`, `message` |
| `/catalogs/:id/export` | `ExportComponent` | `button`, `progressbar`, `message`, `panel`, `divider`, `tag` |

---

## Full Component Index (90 total)

### Directives (applied as attributes, NOT component tags)

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [animateonscroll.md](animateonscroll.md) | `primeng/animateonscroll` | `[pAnimateOnScroll]` | IntersectionObserver CSS animation trigger |
| [autofocus.md](autofocus.md) | `primeng/autofocus` | `[pAutoFocus]` | Auto-focus element on mount |
| [inputtext.md](inputtext.md) | `primeng/inputtext` | `[pInputText]` | DIRECTIVE on native `<input>` |
| [inputmask.md](inputmask.md) | `primeng/inputmask` | `[pInputMask]` | DIRECTIVE on native `<input>` |
| [textarea.md](textarea.md) | `primeng/textarea` | `[pTextarea]`, `[pInputTextarea]` | DIRECTIVE on native `<textarea>` |
| [tooltip.md](tooltip.md) | `primeng/tooltip` | `[pTooltip]` | DIRECTIVE on any element |

### Form Components (ControlValueAccessor — use with `formControlName`)

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [checkbox.md](checkbox.md) | `primeng/checkbox` | `p-checkbox` | Boolean or value-based; CVA |
| [colorpicker.md](colorpicker.md) | `primeng/colorpicker` | `p-colorpicker` | Hex/RGB/HSB picker; CVA |
| [datepicker.md](datepicker.md) | `primeng/datepicker` | `p-datepicker` | Date/range/time picker; CVA |
| [inputnumber.md](inputnumber.md) | `primeng/inputnumber` | `p-inputnumber` | Formatted number input; CVA |
| [inputotp.md](inputotp.md) | `primeng/inputotp` | `p-inputotp`, `p-inputOtp` | OTP digit slots; CVA |
| [knob.md](knob.md) | `primeng/knob` | `p-knob` | Circular range input; CVA |
| [listbox.md](listbox.md) | `primeng/listbox` | `p-listbox` | Scrollable option list; CVA |
| [multiselect.md](multiselect.md) | `primeng/multiselect` | `p-multiselect` | Multi-value dropdown; CVA |
| [password.md](password.md) | `primeng/password` | `p-password` | Password with strength meter; CVA |
| [radiobutton.md](radiobutton.md) | `primeng/radiobutton` | `p-radiobutton` | Single radio in a group; CVA |
| [rating.md](rating.md) | `primeng/rating` | `p-rating` | Star rating; CVA |
| [select.md](select.md) | `primeng/select` | `p-select` | Dropdown (replaces p-dropdown); CVA |
| [selectbutton.md](selectbutton.md) | `primeng/selectbutton` | `p-selectbutton` | Toggle button group; CVA |
| [slider.md](slider.md) | `primeng/slider` | `p-slider` | Range slider (single or range); CVA |
| [togglebutton.md](togglebutton.md) | `primeng/togglebutton` | `p-togglebutton` | On/Off toggle button; CVA |
| [toggleswitch.md](toggleswitch.md) | `primeng/toggleswitch` | `p-toggleswitch` | iOS-style toggle switch; CVA |
| [treeselect.md](treeselect.md) | `primeng/treeselect` | `p-treeselect` | Hierarchical dropdown; CVA |

### Data Display

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [carousel.md](carousel.md) | `primeng/carousel` | `p-carousel` | Item carousel |
| [dataview.md](dataview.md) | `primeng/dataview` | `p-dataview` | List/grid view with filters |
| [galleria.md](galleria.md) | `primeng/galleria` | `p-galleria` | Image gallery |
| [orderlist.md](orderlist.md) | `primeng/orderlist` | `p-orderlist` | Reorderable list |
| [organizationchart.md](organizationchart.md) | `primeng/organizationchart` | `p-organizationchart` | Org tree chart |
| [paginator.md](paginator.md) | `primeng/paginator` | `p-paginator` | Standalone paginator |
| [picklist.md](picklist.md) | `primeng/picklist` | `p-picklist` | Two-list transfer |
| [scroller.md](scroller.md) | `primeng/scroller` | `p-scroller`, `p-virtualscroller` | Virtual scroll container |
| [table.md](table.md) | `primeng/table` | `p-table` | Full-featured data table |
| [timeline.md](timeline.md) | `primeng/timeline` | `p-timeline` | Event timeline |
| [tree.md](tree.md) | `primeng/tree` | `p-tree` | Hierarchical tree |
| [treetable.md](treetable.md) | `primeng/treetable` | `p-treetable` | Tree + table hybrid |

### Layout

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [accordion.md](accordion.md) | `primeng/accordion` | `p-accordion` + `p-accordionpanel` etc. | Composable accordion |
| [card.md](card.md) | `primeng/card` | `p-card` | Content card with header/footer |
| [divider.md](divider.md) | `primeng/divider` | `p-divider` | Horizontal/vertical separator |
| [fieldset.md](fieldset.md) | `primeng/fieldset` | `p-fieldset` | Collapsible fieldset group |
| [fluid.md](fluid.md) | `primeng/fluid` | `p-fluid` | Full-width form layout wrapper |
| [iftalabel.md](iftalabel.md) | `primeng/iftalabel` | `p-iftalabel` | IFTA-style persistent label |
| [floatlabel.md](floatlabel.md) | `primeng/floatlabel` | `p-floatlabel` | Floating label wrapper; variant: in/over/on |
| [iconfield.md](iconfield.md) | `primeng/iconfield` | `p-iconfield` | Input with icon slot |
| [inputgroup.md](inputgroup.md) | `primeng/inputgroup` | `p-inputgroup` | Input with addons |
| [inputgroupaddon.md](inputgroupaddon.md) | `primeng/inputgroupaddon` | `p-inputgroupaddon` | Addon slot for p-inputgroup |
| [inputicon.md](inputicon.md) | `primeng/inputicon` | `p-inputicon` | Icon inside p-iconfield |
| [panel.md](panel.md) | `primeng/panel` | `p-panel` | Collapsible content panel |
| [scrollpanel.md](scrollpanel.md) | `primeng/scrollpanel` | `p-scrollpanel` | Custom scrollbar panel |
| [splitter.md](splitter.md) | `primeng/splitter` | `p-splitter` | Resizable panel split |
| [stepper.md](stepper.md) | `primeng/stepper` | `p-stepper` | Composable step wizard |
| [tabs.md](tabs.md) | `primeng/tabs` | `p-tabs` + `p-tablist` + `p-tab` + `p-tabpanels` + `p-tabpanel` | Composable tabs |
| [toolbar.md](toolbar.md) | `primeng/toolbar` | `p-toolbar` | Start/center/end toolbar |

### Overlays

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [confirmdialog.md](confirmdialog.md) | `primeng/confirmdialog` | `p-confirmdialog` | Confirmation modal (ConfirmationService) |
| [confirmpopup.md](confirmpopup.md) | `primeng/confirmpopup` | `p-confirmpopup` | Inline confirmation popup |
| [dialog.md](dialog.md) | `primeng/dialog` | `p-dialog` | Modal dialog |
| [drawer.md](drawer.md) | `primeng/drawer` | `p-drawer` | Side panel (replaces removed p-sidebar) |
| [dynamicdialog.md](dynamicdialog.md) | `primeng/dynamicdialog` | Programmatic only | DialogService-driven modal |
| [overlay.md](overlay.md) | `primeng/overlay` | `p-overlay` | Low-level overlay host |
| [popover.md](popover.md) | `primeng/popover` | `p-popover` | Popover overlay |
| [toast.md](toast.md) | `primeng/toast` | `p-toast` | Notification toasts (MessageService) |

### Navigation

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [breadcrumb.md](breadcrumb.md) | `primeng/breadcrumb` | `p-breadcrumb` | Breadcrumb trail |
| [contextmenu.md](contextmenu.md) | `primeng/contextmenu` | `p-contextmenu` | Right-click context menu |
| [dock.md](dock.md) | `primeng/dock` | `p-dock` | macOS-style dock |
| [megamenu.md](megamenu.md) | `primeng/megamenu` | `p-megamenu` | Multi-column mega menu |
| [menu.md](menu.md) | `primeng/menu` | `p-menu` | Simple popup/static menu |
| [menubar.md](menubar.md) | `primeng/menubar` | `p-menubar` | Horizontal menu bar |
| [panelmenu.md](panelmenu.md) | `primeng/panelmenu` | `p-panelmenu` | Accordion sidebar menu |
| [speeddial.md](speeddial.md) | `primeng/speeddial` | `p-speeddial` | FAB with action items |
| [splitbutton.md](splitbutton.md) | `primeng/splitbutton` | `p-splitbutton` | Button + dropdown menu |
| [steps.md](steps.md) | `primeng/steps` | `p-steps` | Wizard progress indicator |
| [tieredmenu.md](tieredmenu.md) | `primeng/tieredmenu` | `p-tieredmenu` | Nested submenu |

### Buttons

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [button.md](button.md) | `primeng/button` | `p-button` or `[pButton]` | Primary action button; `[pButton]` on native `<button>` |
| [buttongroup.md](buttongroup.md) | `primeng/buttongroup` | `p-buttongroup` | Groups buttons |

### Media

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [chart.md](chart.md) | `primeng/chart` | `p-chart` | Chart.js wrapper (class: `UIChart`) |
| [editor.md](editor.md) | `primeng/editor` | `p-editor` | Quill rich text editor |
| [image.md](image.md) | `primeng/image` | `p-image` | Image with preview/zoom |
| [imagecompare.md](imagecompare.md) | `primeng/imagecompare` | `p-imagecompare` | Before/after image slider |
| [inplace.md](inplace.md) | `primeng/inplace` | `p-inplace` | Click-to-edit inline display |

### File

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [fileupload.md](fileupload.md) | `primeng/fileupload` | `p-fileupload` | File upload with drag-drop |

### Feedback

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [badge.md](badge.md) | `primeng/badge` | `p-badge` or `[pBadge]` | Numeric/dot badge |
| [blockui.md](blockui.md) | `primeng/blockui` | `p-blockui` | Block/overlay a target element |
| [message.md](message.md) | `primeng/message` | `p-message` | Inline status message (no `text` prop — use content) |
| [metergroup.md](metergroup.md) | `primeng/metergroup` | `p-metergroup` | Multi-segment meter bar |
| [overlaybadge.md](overlaybadge.md) | `primeng/overlaybadge` | `p-overlaybadge` | Badge positioned over an element |
| [progressbar.md](progressbar.md) | `primeng/progressbar` | `p-progressbar` | Determinate/indeterminate progress |
| [progressspinner.md](progressspinner.md) | `primeng/progressspinner` | `p-progressspinner` | Animated spinner |
| [skeleton.md](skeleton.md) | `primeng/skeleton` | `p-skeleton` | Loading placeholder |
| [tag.md](tag.md) | `primeng/tag` | `p-tag` | Colored label chip |

### Misc

| File | Import | Selector | Notes |
|------|--------|----------|-------|
| [animateonscroll.md](animateonscroll.md) | `primeng/animateonscroll` | `[pAnimateOnScroll]` | Scroll-triggered animation |
| [autofocus.md](autofocus.md) | `primeng/autofocus` | `[pAutoFocus]` | Auto-focus on mount |
| [avatar.md](avatar.md) | `primeng/avatar` | `p-avatar` | User avatar (text/icon/image) |
| [avatargroup.md](avatargroup.md) | `primeng/avatargroup` | `p-avatargroup` | Stacked avatar group |
| [cascadeselect.md](cascadeselect.md) | `primeng/cascadeselect` | `p-cascadeselect` | Nested dropdown select |
| [chip.md](chip.md) | `primeng/chip` | `p-chip` | Dismissible label chip |
| [scrolltop.md](scrolltop.md) | `primeng/scrolltop` | `p-scrolltop` | Back-to-top button |
| [terminal.md](terminal.md) | `primeng/terminal` | `p-terminal` | CLI-style terminal |

### Icons

| File | Notes |
|------|-------|
| [icons.md](icons.md) | PrimeIcons `pi pi-*` class reference; common icon table for MeeSell |

---

## Key Patterns

### Directive vs Component

Some "components" are actually DIRECTIVES applied to native elements. These are easy to misuse:

| Directive | Applied to |
|-----------|-----------|
| `[pInputText]` | `<input>` |
| `[pInputMask]` | `<input>` |
| `[pTextarea]` | `<textarea>` |
| `[pTooltip]` | Any element |
| `[pAnimateOnScroll]` | Any element |
| `[pAutoFocus]` | Any focusable element |
| `[pButton]` | `<button>` |
| `[pBadge]` | Any element |

### Signal Two-Way Binding

When using Angular `signal()` with PrimeNG's two-way bound inputs (e.g., `Tabs.value`, `Stepper.value`, `Drawer.visible`):

```typescript
// Correct — split the binding
[visible]="drawerOpen()" (visibleChange)="drawerOpen.set($event)"

// Or use the shorthand [(visible)] only when the left side is a ModelSignal
[(visible)]="drawerOpen"  // works if drawerOpen is a signal()
```

### ControlValueAccessor Components

All CVA components work identically in reactive forms:

```html
<p-select formControlName="category" [options]="categoryOpts" />
<p-checkbox formControlName="active" [binary]="true" />
<p-slider formControlName="margin" [min]="0" [max]="100" />
```

### MessageService (Toast + ConfirmationService)

Provide at app level in `app.config.ts`:

```typescript
providers: [
  MessageService,
  ConfirmationService,
]
```

Then inject anywhere:

```typescript
readonly msgSvc = inject(MessageService);
msgSvc.add({ severity: 'success', summary: 'Done', detail: 'Saved.' });
```

### Deprecated Selectors (do NOT use)

| Deprecated | Use instead |
|-----------|-------------|
| `p-sidebar` | `p-drawer` |
| `p-dropdown` | `p-select` |
| `p-tabView` / `p-tabPanel` | `p-tabs` / `p-tablist` / `p-tab` / `p-tabpanels` / `p-tabpanel` |
| `p-accordionTab` | `p-accordion` + `p-accordionpanel` + `p-accordionheader` + `p-accordioncontent` |
