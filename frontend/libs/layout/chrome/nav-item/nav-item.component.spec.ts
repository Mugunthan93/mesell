import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MeeNavItemComponent } from './nav-item.component';

describe('MeeNavItemComponent', () => {
  let fixture: ComponentFixture<MeeNavItemComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeNavItemComponent, NoopAnimationsModule],
      // Wildcard route so clicking the real routerLink resolves cleanly (no
      // "cannot match" error reported after teardown → no NG0205 noise).
      providers: [provideRouter([{ path: '**', children: [] }])],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeNavItemComponent);
    fixture.componentRef.setInput('route', '/dashboard');
    fixture.componentRef.setInput('label', 'Dashboard');
    fixture.componentRef.setInput('icon', 'dashboard');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render an a.nav-item with the label', () => {
    const a = fixture.nativeElement.querySelector('a.nav-item');
    expect(a).toBeTruthy();
    expect(a.textContent).toContain('Dashboard');
  });

  it('should not be accent by default', () => {
    expect(fixture.nativeElement.querySelector('.nav-item--accent')).toBeNull();
  });

  it('should add .nav-item--accent when accent=true', () => {
    fixture.componentRef.setInput('accent', true);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.nav-item--accent')).toBeTruthy();
  });

  it('should emit navigated on click', () => {
    let emitted = false;
    fixture.componentInstance.navigated.subscribe(() => (emitted = true));
    fixture.nativeElement.querySelector('a.nav-item').click();
    expect(emitted).toBe(true);
  });
});
