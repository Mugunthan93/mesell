import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeTableComponent } from './table.component';
import type { MeeColumn } from './table.types';

const MOCK_COLUMNS: MeeColumn[] = [
  { field: 'name', header: 'Name' },
  { field: 'status', header: 'Status' },
];

const MOCK_ROWS = [
  { name: 'Product A', status: 'active' },
  { name: 'Product B', status: 'draft' },
];

describe('MeeTableComponent', () => {
  let fixture: ComponentFixture<MeeTableComponent>;
  let comp: MeeTableComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeTableComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeTableComponent);
    comp = fixture.componentInstance;
    fixture.componentRef.setInput('columns', MOCK_COLUMNS);
    fixture.componentRef.setInput('rows', MOCK_ROWS);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default loading to false', () => {
    expect(comp.loading()).toBe(false);
  });

  it('should emit row_click on row click', () => {
    let emitted: unknown = null;
    comp.row_click.subscribe((row: unknown) => { emitted = row; });
    comp.row_click.emit(MOCK_ROWS[0]);
    expect(emitted).toEqual(MOCK_ROWS[0]);
  });

  it('should emit page event', () => {
    let emitted: { first: number; rows: number } | null = null;
    comp.page.subscribe((e) => { emitted = e; });
    comp.onPage({ first: 10, rows: 10 });
    expect(emitted).toEqual({ first: 10, rows: 10 });
  });
});
