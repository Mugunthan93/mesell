// features/landing/landing/landing.component.spec.ts
// Unit tests for LandingComponent
// Pattern: Vitest + Angular TestBed (zoneless) + TranslocoTestingModule
// per dashboard.component.spec.ts established pattern

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { describe, expect, it, beforeEach } from 'vitest';

import { LandingComponent } from './landing.component';

// ── i18n test translations ──
const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'nav.login': 'Log in',
      'nav.signup': 'Sign up',
      'landing.hero.headline': 'Sell smarter on Meesho',
      'landing.hero.subheadline': 'AI-powered catalog creation in minutes',
      'landing.cta.signup': 'Get started free',
      'landing.cta.login': 'Already a member? Log in',
      'landing.value.catalog.title': 'Catalog in minutes',
      'landing.value.catalog.body': 'Upload products and let AI fill in the details. No more typing for every field.',
      'landing.value.quality.title': 'Check quality before you list',
      'landing.value.quality.body': 'Catch image and content errors before Meesho rejects your upload.',
      'landing.value.pricing.title': 'Price to win',
      'landing.value.pricing.body': 'See your profit margin before you set the price. No guesswork.',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Test Suite ──

describe('LandingComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        LandingComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
      ],
    }).compileComponents();
  });

  // ── Test 1: renders brand name in navbar ──

  it('renders brand name "MeeSell" in the navbar', async () => {
    const fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const brand = el.querySelector('header span');
    expect(brand?.textContent?.trim()).toBe('MeeSell');
  });

  // ── Test 2: renders hero headline via transloco ──

  it('renders the hero headline from transloco', async () => {
    const fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const headline = el.querySelector('#hero-headline');
    expect(headline?.textContent?.trim()).toBe('Sell smarter on Meesho');
  });

  // ── Test 3: "Sign up" button is present with routerLink="/signup" ──

  it('renders a Sign up element with routerLink="/signup"', async () => {
    const fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    // Select the navbar signup link (has routerLink="/signup")
    const signupLinks: NodeListOf<HTMLAnchorElement> = el.querySelectorAll('a[routerlink="/signup"], a[ng-reflect-router-link="/signup"]');
    expect(signupLinks.length).toBeGreaterThan(0);
  });

  // ── Test 4: "Log in" link is present with routerLink="/login" ──

  it('renders a Log in link with routerLink="/login"', async () => {
    const fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const loginLinks: NodeListOf<HTMLAnchorElement> = el.querySelectorAll('a[routerlink="/login"], a[ng-reflect-router-link="/login"]');
    expect(loginLinks.length).toBeGreaterThan(0);
  });

  // ── Test 5: renders exactly 3 value-prop cards ──

  it('renders 3 value prop cards', async () => {
    const fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    // Each value-prop card is an <article> element
    const cards = el.querySelectorAll('article');
    expect(cards.length).toBe(3);
  });

  // ── Test 6: footer contains copyright text ──

  it('renders footer copyright text', async () => {
    const fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const footer = el.querySelector('footer');
    expect(footer?.textContent).toContain('2026 MeeSell');
    expect(footer?.textContent).toContain('Built for Indian Meesho sellers');
  });
});
