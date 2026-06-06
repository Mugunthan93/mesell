// features/export/export/export.component.spec.ts

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExportComponent } from './export.component';
import { provideAnimations } from '@angular/platform-browser/animations';
import { Component, input } from '@angular/core';

// Stub StatusBadgeComponent to avoid full dependency tree in unit test
@Component({
  selector: 'mee-status-badge',
  standalone: true,
  template: '<span class="badge-stub">{{ status() }}</span>',
})
class StatusBadgeStub {
  readonly status = input.required<string>();
}

describe('ExportComponent', () => {
  let fixture: ComponentFixture<ExportComponent>;
  let component: ExportComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExportComponent],
      providers: [provideAnimations()],
    })
      .overrideComponent(ExportComponent, {
        remove: { imports: [] },
        add: { imports: [StatusBadgeStub] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(ExportComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render "Export Catalog" heading', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Export Catalog');
  });

  it('should render the ready-to-export summary text', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('8 products ready to export');
  });

  it('should render the draft warning banner', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('3 products are still in Draft state');
  });

  it('should render "Export History" section', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Export History');
  });

  it('should render 2 history rows', () => {
    expect(component.historyRows.length).toBe(2);
    expect(component.historyRows[0].status).toBe('ready');
    expect(component.historyRows[1].status).toBe('failed');
  });

  it('should render the export button', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Export to Meesho CSV');
  });
});
