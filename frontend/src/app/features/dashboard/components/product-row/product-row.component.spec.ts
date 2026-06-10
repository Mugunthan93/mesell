// features/dashboard/components/product-row/product-row.component.spec.ts
// Unit tests for ProductRowComponent — 4 tests per dispatch acceptance criteria.
// Pattern: Vitest + Angular TestBed (zoneless) per dashboard.component.spec.ts pattern.
//
// Template pattern note: click handlers receive row() as a parameter (evaluated in the
// template context, not from this.row()). Tests 2 and 3 call onEdit(row)/onDeleteRequest(row)
// directly with the row value — no NG0950 risk since the methods accept the value.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { outputToObservable } from '@angular/core/rxjs-interop';
import { describe, expect, it, beforeEach } from 'vitest';
import { By } from '@angular/platform-browser';
import { OverlayContainer } from '@angular/cdk/overlay';

// ɵresolveComponentResources: same styleUrl/jsdom pattern as dashboard.component.spec.ts.
// Must be called before configureTestingModule to clear the "pending resolution" state
// on components with styleUrl. No-op resolver (empty string) is correct for unit tests.
import { ɵresolveComponentResources as resolveComponentResources } from '@angular/core';

import { ProductRowComponent } from './product-row.component';
import { ProductListItem } from '../../dashboard-api.service';

// ── Helpers ──

function makeRow(overrides: Partial<ProductListItem> = {}): ProductListItem {
  return {
    product_id: 'prod-001',
    name: 'Blue Kurti',
    category_id: 'cat-abc',
    status: 'draft',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-06-01T12:00:00Z',
    ...overrides,
  };
}

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'dashboard.row.actions': 'Actions',
      'dashboard.row.edit': 'Edit catalog',
      'dashboard.row.delete': 'Delete',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Test Suite ──

describe('ProductRowComponent', () => {
  let overlayContainerElement: HTMLElement;

  beforeEach(async () => {
    // Resolve component resources BEFORE configureTestingModule.
    // Angular JIT fires assertComponentIsResolved when queuing types, so
    // styleUrl must be resolved before configureTestingModule is called.
    await resolveComponentResources(() => Promise.resolve(''));

    await TestBed.configureTestingModule({
      imports: [
        ProductRowComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
      ],
    }).compileComponents();

    overlayContainerElement = TestBed.inject(OverlayContainer).getContainerElement();
  });

  // ── Test 1: Renders the kebab menu trigger button ──

  it('renders the kebab menu trigger button', async () => {
    const fixture = TestBed.createComponent(ProductRowComponent);
    fixture.componentRef.setInput('row', makeRow());
    fixture.detectChanges();
    await fixture.whenStable();

    const triggerButton = fixture.nativeElement.querySelector(
      'button[mat-icon-button]',
    );
    expect(triggerButton).toBeTruthy();

    // Verify the more_vert icon is inside the button
    const icon = triggerButton.querySelector('mat-icon');
    expect(icon).toBeTruthy();
    expect(icon.textContent?.trim()).toBe('more_vert');
  });

  // ── Test 2: Emits editRequest with the row when Edit is clicked ──
  // Calls onEdit(row) directly — method accepts row as parameter (no this.row() read).
  // This matches how the template calls it: (click)="onEdit(row())".

  it('emits editRequest with the row when Edit is clicked', async () => {
    const fixture = TestBed.createComponent(ProductRowComponent);
    const component = fixture.componentInstance;
    const row = makeRow({ product_id: 'prod-edit-001', name: 'Edit Me' });

    fixture.componentRef.setInput('row', row);
    fixture.detectChanges();
    await fixture.whenStable();

    const emitted: ProductListItem[] = [];
    const sub = outputToObservable(component.editRequest).subscribe(
      (v) => emitted.push(v),
    );

    // Call onEdit() with the row value directly — matches template: (click)="onEdit(row())"
    component.onEdit(row);

    sub.unsubscribe();

    expect(emitted.length).toBe(1);
    expect(emitted[0].product_id).toBe('prod-edit-001');
    expect(emitted[0].name).toBe('Edit Me');
  });

  // ── Test 3: Emits deleteRequest with the row when Delete is clicked ──
  // Calls onDeleteRequest(row) directly — parent handles dialog; component only emits.

  it('emits deleteRequest with the row when Delete is clicked', async () => {
    const fixture = TestBed.createComponent(ProductRowComponent);
    const component = fixture.componentInstance;
    const row = makeRow({ product_id: 'prod-del-001', name: 'Delete Me' });

    fixture.componentRef.setInput('row', row);
    fixture.detectChanges();
    await fixture.whenStable();

    const emitted: ProductListItem[] = [];
    const sub = outputToObservable(component.deleteRequest).subscribe(
      (v) => emitted.push(v),
    );

    // Call onDeleteRequest() with the row value directly
    // Matches template: (click)="onDeleteRequest(row())"
    component.onDeleteRequest(row);

    sub.unsubscribe();

    expect(emitted.length).toBe(1);
    expect(emitted[0].product_id).toBe('prod-del-001');
    expect(emitted[0].name).toBe('Delete Me');
  });

  // ── Test 4: Delete menu item has mee-action--destructive class ──

  it('applies mee-action--destructive class to the Delete menu item', async () => {
    const fixture = TestBed.createComponent(ProductRowComponent);
    fixture.componentRef.setInput('row', makeRow());
    fixture.detectChanges();
    await fixture.whenStable();

    // Open the menu programmatically via the trigger button
    const trigger = fixture.debugElement.query(By.css('button[mat-icon-button]'));
    expect(trigger).toBeTruthy();

    trigger.nativeElement.click();
    fixture.detectChanges();
    await fixture.whenStable();

    // MatMenu items render in a CDK overlay — query via the OverlayContainer element
    const destructiveBtn = overlayContainerElement.querySelector('.mee-action--destructive');
    expect(destructiveBtn).toBeTruthy();
  });
});
