// features/landing/landing/landing.component.ts
// Route: / — public home page (no auth required, no API calls)
// per FRONTEND_ARCHITECTURE.md §2.C.1
// Dispatch: auth sub-session dispatch 1 of N (2026-06-06)

import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'mee-landing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'mee-landing' },
  imports: [
    RouterLink,
    MatButtonModule,
    TranslocoModule,
  ],
  template: `
    <!-- Section 1: Top navbar strip -->
    <header class="sticky top-0 z-50 bg-bg-elevated shadow-mee-1 px-4 py-3">
      <nav
        class="max-w-5xl mx-auto flex items-center justify-between"
        aria-label="MeeSell main navigation"
      >
        <span class="font-bold text-mee-xl text-on-surface">MeeSell</span>

        <div class="flex items-center gap-4">
          <a
            routerLink="/login"
            class="text-mee-sm text-on-surface-variant hover:text-primary transition duration-standard no-underline min-h-[44px] inline-flex items-center"
          >{{ 'nav.login' | transloco }}</a>

          <a
            routerLink="/signup"
            mat-flat-button
            color="primary"
            class="min-h-[44px] min-w-[44px]"
            aria-label="Sign up for MeeSell"
          >{{ 'nav.signup' | transloco }}</a>
        </div>
      </nav>
    </header>

    <!-- Section 2: Hero -->
    <section class="bg-bg py-12 md:py-20" aria-labelledby="hero-headline">
      <div class="max-w-2xl mx-auto px-4 text-center">
        <h1
          id="hero-headline"
          class="text-mee-3xl md:text-mee-4xl font-bold text-on-surface leading-tight"
        >{{ 'landing.hero.headline' | transloco }}</h1>

        <p class="text-mee-lg text-on-surface-variant mt-3">
          {{ 'landing.hero.subheadline' | transloco }}
        </p>

        <div class="mt-8">
          <a
            routerLink="/signup"
            mat-flat-button
            color="primary"
            class="rounded-mee-full px-8 py-3 text-mee-base font-semibold min-h-[44px]"
            aria-label="Get started free"
          >{{ 'landing.cta.signup' | transloco }}</a>
        </div>

        <p class="mt-3">
          <a
            routerLink="/login"
            class="text-mee-sm text-on-surface-variant hover:text-primary transition duration-standard no-underline min-h-[44px] inline-flex items-center"
          >{{ 'landing.cta.login' | transloco }}</a>
        </p>
      </div>
    </section>

    <!-- Section 3: Value props (3 cards) -->
    <section
      class="max-w-5xl mx-auto px-4 py-12 grid grid-cols-1 md:grid-cols-3 gap-6"
      aria-label="Why MeeSell"
    >
      <article class="bg-surface rounded-mee-md shadow-mee-1 p-6 flex flex-col gap-3">
        <span class="material-symbols-outlined text-primary text-[2rem]" aria-hidden="true">inventory_2</span>
        <h2 class="text-mee-lg font-semibold text-on-surface">
          {{ 'landing.value.catalog.title' | transloco }}
        </h2>
        <p class="text-mee-sm text-on-surface-variant leading-relaxed">
          {{ 'landing.value.catalog.body' | transloco }}
        </p>
      </article>

      <article class="bg-surface rounded-mee-md shadow-mee-1 p-6 flex flex-col gap-3">
        <span class="material-symbols-outlined text-primary text-[2rem]" aria-hidden="true">task_alt</span>
        <h2 class="text-mee-lg font-semibold text-on-surface">
          {{ 'landing.value.quality.title' | transloco }}
        </h2>
        <p class="text-mee-sm text-on-surface-variant leading-relaxed">
          {{ 'landing.value.quality.body' | transloco }}
        </p>
      </article>

      <article class="bg-surface rounded-mee-md shadow-mee-1 p-6 flex flex-col gap-3">
        <span class="material-symbols-outlined text-primary text-[2rem]" aria-hidden="true">trending_up</span>
        <h2 class="text-mee-lg font-semibold text-on-surface">
          {{ 'landing.value.pricing.title' | transloco }}
        </h2>
        <p class="text-mee-sm text-on-surface-variant leading-relaxed">
          {{ 'landing.value.pricing.body' | transloco }}
        </p>
      </article>
    </section>

    <!-- Section 4: Footer strip -->
    <footer class="bg-surface-variant py-6 px-4 text-center text-mee-xs text-on-surface-variant">
      &copy; 2026 MeeSell. Built for Indian Meesho sellers.
    </footer>
  `,
})
export class LandingComponent {}
