## Session 2026-06-06 — Auth Dispatch 1 — LandingComponent {#landing-dispatch-1}

### Route touched
`/` — features/landing/landing/

### Services consumed
None. LandingComponent is fully static (public route, no auth, no API calls).

### Pattern: | transloco pipe — NOT *transloco="let t" structural directive
- Task spec stated to use `*transloco="let t"` but NO component in this codebase uses that pattern.
- ALL components (dashboard, profile) use `| transloco` pipe directly in interpolation: `{{ 'key' | transloco }}`.
- `TranslocoModule` import covers BOTH the pipe and the structural directive — import is the same.
- DO NOT introduce `*transloco="let t"` pattern. Follow existing codebase convention.
- Stop condition in the spec said "check features/dashboard/" — that confirmed pipe pattern is canonical.

### Pattern: Static page — no CommonModule, no @if/@for needed
- LandingComponent has zero conditional blocks and zero lists.
- Angular 18 native control flow (@if/@for) is available without CommonModule but is not needed here.
- Minimal import list for a static page: `[RouterLink, MatButtonModule, TranslocoModule]`.

### Pattern: host binding via { class: 'mee-landing' } in @Component metadata
- Prefer `host: { class: '...' }` over `@HostBinding('class')` for standalone components.
- Cleaner, co-located with the component decorator, no extra property needed.

### Pattern: Material Symbols Outlined icons (not mat-icon / MatIconModule)
- `<span class="material-symbols-outlined" aria-hidden="true">icon_name</span>`
- Material Symbols Outlined is the newer icon font family loaded globally via _typography.scss.
- `mat-icon` uses the older Material Icons family — do NOT mix families.
- `aria-hidden="true"` required on all decorative icon spans.

### Pattern: routerLink anchor + mat-flat-button for CTA buttons
- `<a routerLink="/route" mat-flat-button color="primary">text</a>` — correct Angular pattern.
- Avoids `<button (click)="router.navigate(...)">` for routes that should be linkable (right-click
  → open in new tab, keyboard navigation).
- Apply `min-h-[44px]` on the anchor for 44px touch target compliance.

### Pattern: 44px touch targets on text links
- Text `<a>` links get `min-h-[44px] inline-flex items-center` for Tirupur mobile-first compliance.
- This is a Tailwind utility approach; no explicit height/padding needed when `inline-flex items-center`
  expands the tap area vertically via the parent line height context.

### Pattern: Semantic HTML5 for static landing sections
- Use `<header>`, `<nav>`, `<section>`, `<article>`, `<footer>` (not generic `<div>`).
- `aria-labelledby` on `<section>` pointing to the heading id (`id="hero-headline"`).
- `aria-label` on `<nav>` and on decorative icon sections.
- This satisfies WCAG 2.2 AA landmark navigation without any CDK a11y dependency.

### Build result (2026-06-06)
- landing-component lazy chunk: 3.71 kB raw / 1.31 kB gzip (budget: ≤80 kB — 98% headroom)
- 6/6 vitest tests passing
- ng build --configuration=production: ZERO errors

---
