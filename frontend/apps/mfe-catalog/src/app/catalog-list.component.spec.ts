/**
 * catalog-list.component.spec.ts — catalog-list-delete feature (component layer)
 *
 * Tests:
 *  1.  Real API wired: listProducts called in ngOnInit (simulation stub removed).
 *  2.  Renders one catalog-row per item; data-product-id matches wire id.
 *  3.  Does NOT render simulated ids cat-001/cat-002/cat-003.
 *  4.  catalog-empty shown when service returns empty list.
 *  5.  catalog-empty absent when list has items.
 *  6.  Per-row testids (catalog-row, catalog-edit-btn, catalog-delete-btn) on native elements.
 *  7.  onDelete(id) opens inline confirm (catalog-delete-confirm / catalog-delete-cancel visible).
 *  8.  confirm affordance hides edit/delete buttons while open.
 *  9.  onDeleteCancel() reverts to normal action row.
 *  10. onDeleteConfirm(id) calls service.deleteProduct(id).
 *  11. Row removed from DOM on complete (204/404/401 — success cases).
 *  12. toast.error() NOT called on success.
 *  13. Empty state shown after the last row is deleted.
 *  14. toast.error() called on 5xx; row kept in DOM.
 *  15. confirm affordance hidden after 5xx (row stays, confirm resets).
 *  16. Double-submit guard: second onDeleteConfirm while in-flight is a no-op.
 *
 * Harness pattern (ONE outer describe, ONE beforeEach — avoids "TestBed already
 * instantiated" when the Angular Vitest runner does not auto-reset between nested
 * describe groups with independent beforeEach calls):
 *   - Single TestBed.configureTestingModule per test lifecycle.
 *   - Mock services accept configurable override functions set per-test via the
 *     `mockOverride` object before `fixture.detectChanges()`.
 *   - No HttpTestingController (service mocked at Observable level).
 *   - No fakeAsync/tick (zone-testing.js absent; all mocks return sync observables).
 *   - Double-submit test uses a Subject to hold the delete observable open.
 */

import {
  TestBed,
  ComponentFixture,
} from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Subject, EMPTY, of, throwError } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import { CatalogListComponent } from './catalog-list.component';
import { CatalogListApiService } from './catalog-list-api.service';
import { MeeToastService } from '@mesell/ui-kit';
import type { CatalogListResponse } from './catalog-list.model';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const ITEM_A: CatalogListResponse['items'][0] = {
  id:        'prod-uuid-001',
  name:      'Blue Kurti Collection',
  status:    'ready',
  updatedAt: '2026-06-20T00:00:00Z',
};

const ITEM_B: CatalogListResponse['items'][0] = {
  id:        'prod-uuid-002',
  name:      'Silk Saree Set',
  status:    'draft',
  updatedAt: '2026-06-19T00:00:00Z',
};

const TWO_ITEM_RESPONSE: CatalogListResponse = {
  items: [ITEM_A, ITEM_B],
  total: 2, page: 1, limit: 20,
};

const ONE_ITEM_RESPONSE: CatalogListResponse = {
  items: [ITEM_A],
  total: 1, page: 1, limit: 20,
};

const EMPTY_RESPONSE: CatalogListResponse = {
  items: [],
  total: 0, page: 1, limit: 20,
};

// ── DOM helpers ───────────────────────────────────────────────────────────────

function getRows(fixture: ComponentFixture<CatalogListComponent>): NodeListOf<HTMLElement> {
  return (fixture.nativeElement as HTMLElement).querySelectorAll('[data-testid="catalog-row"]');
}

function getByTestid(fixture: ComponentFixture<CatalogListComponent>, testid: string): HTMLElement | null {
  return (fixture.nativeElement as HTMLElement).querySelector(`[data-testid="${testid}"]`);
}

// ── Configurable mock state ───────────────────────────────────────────────────
// Each test sets `mockState` before detectChanges() to control service behavior.

interface MockState {
  listResponse: CatalogListResponse;
  // deleteSubject: if set, deleteProduct returns this Subject (for in-flight control).
  deleteSubject: Subject<void> | null;
  // deleteResult: 'complete' → EMPTY; 'error' → 5xx throwError; ignored when deleteSubject set.
  deleteResult: 'complete' | 'error';
}

let mockState: MockState;
let listSpy:   ReturnType<typeof vi.fn>;
let deleteSpy: ReturnType<typeof vi.fn>;
let toastErrorSpy: ReturnType<typeof vi.fn>;

function resetMockState(override: Partial<MockState> = {}): void {
  mockState = {
    listResponse: TWO_ITEM_RESPONSE,
    deleteSubject: null,
    deleteResult: 'complete',
    ...override,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('CatalogListComponent', () => {
  let fixture:   ComponentFixture<CatalogListComponent>;
  let component: CatalogListComponent;

  beforeEach(() => {
    // Ensure TestBed is clean before each test — the Angular Vitest runner does
    // not auto-reset between spec files, so the previous file (e.g. the service
    // spec) may leave TestBed instantiated.  resetTestingModule() is a no-op
    // when TestBed is already clean, so this is safe to call unconditionally.
    TestBed.resetTestingModule();

    // Default mock state — individual tests override before detectChanges().
    resetMockState();

    listSpy = vi.fn(() => of(mockState.listResponse));

    deleteSpy = vi.fn(() => {
      if (mockState.deleteSubject) {
        return mockState.deleteSubject.asObservable();
      }
      return mockState.deleteResult === 'complete'
        ? EMPTY
        : throwError(() => ({ status: 500, message: 'Server error' }));
    });

    toastErrorSpy = vi.fn();

    TestBed.configureTestingModule({
      imports: [CatalogListComponent],
      providers: [
        provideRouter([]),
        {
          provide: CatalogListApiService,
          useValue: {
            listProducts:  listSpy  as unknown as CatalogListApiService['listProducts'],
            deleteProduct: deleteSpy as unknown as CatalogListApiService['deleteProduct'],
          },
        },
        {
          provide: MeeToastService,
          useValue: { error: toastErrorSpy, success: vi.fn() },
        },
      ],
    });

    fixture   = TestBed.createComponent(CatalogListComponent);
    component = fixture.componentInstance;
  });

  // ── Real API wiring ─────────────────────────────────────────────────────────

  it('calls listProducts({ page: 1, limit: 20 }) in ngOnInit', () => {
    fixture.detectChanges();
    expect(listSpy).toHaveBeenCalledWith({ page: 1, limit: 20 });
  });

  it('loading signal is false after listProducts emits synchronously', () => {
    fixture.detectChanges();
    expect(component.loading()).toBe(false);
  });

  // ── Row rendering ───────────────────────────────────────────────────────────

  it('renders one catalog-row per item returned by service', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    expect(getRows(fixture).length).toBe(2);
  });

  it('each catalog-row carries data-product-id matching the item id', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const rows = getRows(fixture);
    expect(rows[0].getAttribute('data-product-id')).toBe(ITEM_A.id);
    expect(rows[1].getAttribute('data-product-id')).toBe(ITEM_B.id);
  });

  it('does NOT render simulated placeholder ids (cat-001/cat-002/cat-003)', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const ids = Array.from(getRows(fixture)).map(r => r.getAttribute('data-product-id'));
    expect(ids).not.toContain('cat-001');
    expect(ids).not.toContain('cat-002');
    expect(ids).not.toContain('cat-003');
  });

  // ── Empty state ─────────────────────────────────────────────────────────────

  it('catalog-empty shown when service returns empty list', () => {
    resetMockState({ listResponse: EMPTY_RESPONSE });
    listSpy.mockReturnValue(of(EMPTY_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-empty')).not.toBeNull();
  });

  it('catalog-empty absent when list has items', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-empty')).toBeNull();
  });

  // ── Per-row testids on native elements ──────────────────────────────────────

  it('catalog-row is a native div element (federation-survivable)', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();
    const el = getByTestid(fixture, 'catalog-row');
    expect(el).not.toBeNull();
    expect(el!.tagName.toLowerCase()).toBe('div');
  });

  it('catalog-edit-btn is present in normal action state', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-edit-btn')).not.toBeNull();
  });

  it('catalog-delete-btn is present in normal action state', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-delete-btn')).not.toBeNull();
  });

  it('catalog-empty is a native div wrapper (not mee-empty-state directly)', () => {
    resetMockState({ listResponse: EMPTY_RESPONSE });
    listSpy.mockReturnValue(of(EMPTY_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();
    const el = getByTestid(fixture, 'catalog-empty');
    expect(el).not.toBeNull();
    expect(el!.tagName.toLowerCase()).toBe('div');
  });

  // ── Delete button → inline confirm ─────────────────────────────────────────

  it('onDelete(id) sets confirmingDeleteId to that id', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    expect(component.confirmingDeleteId()).toBe(ITEM_A.id);
  });

  it('onDelete(id) shows catalog-delete-confirm in the DOM', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-delete-confirm')).not.toBeNull();
  });

  it('onDelete(id) shows catalog-delete-cancel in the DOM', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-delete-cancel')).not.toBeNull();
  });

  it('confirm affordance hides catalog-edit-btn while open', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-edit-btn')).toBeNull();
  });

  it('confirm affordance hides catalog-delete-btn while open', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-delete-btn')).toBeNull();
  });

  it('catalog-delete-confirm absent before onDelete is called', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-delete-confirm')).toBeNull();
  });

  // ── Cancel → reverts to normal state ────────────────────────────────────────

  it('onDeleteCancel() resets confirmingDeleteId to null', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteCancel();
    expect(component.confirmingDeleteId()).toBeNull();
  });

  it('onDeleteCancel() restores catalog-edit-btn', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteCancel();
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-edit-btn')).not.toBeNull();
  });

  it('onDeleteCancel() restores catalog-delete-btn', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteCancel();
    fixture.detectChanges();
    expect(getByTestid(fixture, 'catalog-delete-btn')).not.toBeNull();
  });

  // ── Confirm → service called → row removed ──────────────────────────────────

  it('onDeleteConfirm(id) calls service.deleteProduct(id)', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'complete' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);

    expect(deleteSpy).toHaveBeenCalledWith(ITEM_A.id);
  });

  it('row removed from DOM after successful delete (EMPTY)', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'complete' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);
    fixture.detectChanges();

    expect(getRows(fixture).length).toBe(0);
  });

  it('id removed from catalogs signal after successful delete', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'complete' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);

    expect(component.catalogs().map(r => r.id)).not.toContain(ITEM_A.id);
  });

  it('catalog-delete-confirm hidden after successful delete', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'complete' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);
    fixture.detectChanges();

    expect(getByTestid(fixture, 'catalog-delete-confirm')).toBeNull();
  });

  it('toast.error() NOT called on successful delete', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'complete' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);

    expect(toastErrorSpy).not.toHaveBeenCalled();
  });

  // ── Empty state after last row deleted ──────────────────────────────────────

  it('catalog-empty shown after the last row is deleted', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'complete' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);
    fixture.detectChanges();
    fixture.detectChanges();

    expect(getByTestid(fixture, 'catalog-empty')).not.toBeNull();
  });

  // ── 5xx error → toast + row kept ────────────────────────────────────────────

  it('toast.error() called with delete-failed message on 5xx', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'error' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);
    fixture.detectChanges();

    expect(toastErrorSpy).toHaveBeenCalledWith('Delete failed. Please try again.');
  });

  it('row kept in DOM after 5xx delete', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'error' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);
    fixture.detectChanges();

    expect(getRows(fixture).length).toBe(1);
  });

  it('confirm affordance hidden after 5xx (row stays, confirm resets)', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'error' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);
    fixture.detectChanges();

    expect(getByTestid(fixture, 'catalog-delete-confirm')).toBeNull();
  });

  it('deletingId reset to null after 5xx', () => {
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteResult: 'error' });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();
    component.onDeleteConfirm(ITEM_A.id);

    expect(component.deletingId()).toBeNull();
  });

  // ── Double-submit guard ──────────────────────────────────────────────────────

  it('second onDeleteConfirm while in-flight is a no-op (guard fires)', () => {
    const subject$ = new Subject<void>();
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteSubject: subject$ });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();

    // First call sets deletingId; observable stays pending (subject$ not yet completed)
    component.onDeleteConfirm(ITEM_A.id);
    expect(component.deletingId()).toBe(ITEM_A.id);

    // Second call: guard fires (deletingId === ITEM_A.id) → no-op
    component.onDeleteConfirm(ITEM_A.id);

    expect(deleteSpy).toHaveBeenCalledTimes(1);

    // Cleanup: resolve the pending observable
    subject$.complete();
  });

  it('deletingId set to id while in-flight', () => {
    const subject$ = new Subject<void>();
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteSubject: subject$ });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();

    component.onDeleteConfirm(ITEM_A.id);
    expect(component.deletingId()).toBe(ITEM_A.id);

    // Cleanup
    subject$.complete();
  });

  it('deletingId resets to null when observable completes', () => {
    const subject$ = new Subject<void>();
    resetMockState({ listResponse: ONE_ITEM_RESPONSE, deleteSubject: subject$ });
    listSpy.mockReturnValue(of(ONE_ITEM_RESPONSE));
    fixture.detectChanges();
    fixture.detectChanges();

    component.onDelete(ITEM_A.id);
    fixture.detectChanges();

    component.onDeleteConfirm(ITEM_A.id);
    expect(component.deletingId()).toBe(ITEM_A.id);

    subject$.complete();
    fixture.detectChanges();

    expect(component.deletingId()).toBeNull();
  });
});
