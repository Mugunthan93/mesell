import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeBadgeComponent } from './badge.component';

describe('MeeBadgeComponent', () => {
  let fixture: ComponentFixture<MeeBadgeComponent>;
  let comp: MeeBadgeComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeBadgeComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeBadgeComponent);
    comp = fixture.componentInstance;
    fixture.componentRef.setInput('value', 'Active');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should map neutral severity to secondary', () => {
    fixture.componentRef.setInput('severity', 'neutral');
    expect(comp.pgSeverity()).toBe('secondary');
  });

  it('should map warning severity to warn', () => {
    fixture.componentRef.setInput('severity', 'warning');
    expect(comp.pgSeverity()).toBe('warn');
  });

  it('should map success severity correctly', () => {
    fixture.componentRef.setInput('severity', 'success');
    expect(comp.pgSeverity()).toBe('success');
  });

  it('should map danger severity correctly', () => {
    fixture.componentRef.setInput('severity', 'danger');
    expect(comp.pgSeverity()).toBe('danger');
  });

  it('should map info severity correctly', () => {
    fixture.componentRef.setInput('severity', 'info');
    expect(comp.pgSeverity()).toBe('info');
  });
});
