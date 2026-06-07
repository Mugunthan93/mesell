// super-category-chips.component.spec.ts
// Unit tests for SuperCategoryChipsComponent.
//
// Pattern: Vitest + Angular TestBed (zoneless) + vi.fn() mocks.
// TranslocoTestingModule.forRoot() is in imports[] (not providers[]).
// provideAnimationsAsync('noop') suppresses animation overhead in tests.
// onSelectionChange() is called directly (avoids DOM click simulation)
// to test the emit contract without requiring CDK overlay.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import {
  TranslocoTestingModule,
  TranslocoTestingOptions,
} from '@jsverse/transloco';
import { MatChipListboxChange } from '@angular/material/chips';
import { describe, it, expect, vi } from 'vitest';

import { SuperCategoryChipsComponent } from './super-category-chips.component';

// ── i18n fixture ──

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'onboarding.chips.help':        'Select all categories you sell in.',
      'onboarding.chips.ariaLabel':   'Product super-categories',
      'onboarding.chips.grocery':     'Grocery',
      'onboarding.chips.kids':        'Kids & Baby',
      'onboarding.chips.electronics': 'Electronics',
      'onboarding.chips.beauty':      'Beauty & Health',
      'onboarding.chips.books':       'Books & Stationery',
      'onboarding.chips.appliances':  'Home & Appliances',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Tests ──

describe('SuperCategoryChipsComponent', () => {
  async function setup() {
    await TestBed.configureTestingModule({
      imports: [
        SuperCategoryChipsComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(SuperCategoryChipsComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    return { fixture, component };
  }

  // Test 1: Component instantiates without error
  it('should create', async () => {
    const { component } = await setup();
    expect(component).toBeTruthy();
  });

  // Test 2: Renders exactly 6 chip options
  it('should render exactly 6 chip options', async () => {
    const { fixture } = await setup();
    const chips = fixture.nativeElement.querySelectorAll('mat-chip-option');
    expect(chips.length).toBe(6);
  });

  // Test 3: Emits selectionChange with selected ids when chips are selected
  it('should emit selectionChange with selected ids when chip clicked', async () => {
    const { component } = await setup();
    const emitSpy = vi.spyOn(component.selectionChange, 'emit');

    component.onSelectionChange({
      value: ['26', '16'],
    } as MatChipListboxChange);

    expect(emitSpy).toHaveBeenCalledOnce();
    expect(emitSpy).toHaveBeenCalledWith(['26', '16']);
  });

  // Test 4: Emits empty array when no chips are selected (value is null)
  it('should emit empty array when no chips selected', async () => {
    const { component } = await setup();
    const emitSpy = vi.spyOn(component.selectionChange, 'emit');

    component.onSelectionChange({
      value: null,
    } as unknown as MatChipListboxChange);

    expect(emitSpy).toHaveBeenCalledOnce();
    expect(emitSpy).toHaveBeenCalledWith([]);
  });
});
