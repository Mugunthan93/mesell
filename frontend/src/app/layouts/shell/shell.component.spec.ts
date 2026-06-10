import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Component } from '@angular/core';
import { ShellComponent } from './shell.component';
import { AuthService } from '@mesell/core';

// Minimal stubs for PrimeNG components to avoid jsdom rendering issues
@Component({ selector: 'p-drawer', standalone: true, template: '<ng-content />' })
class DrawerStub {
  visible = false;
  modal = false;
  styleClass = '';
}

@Component({ selector: 'p-menu', standalone: true, template: '' })
class MenuStub {
  model: unknown[] = [];
  popup = false;
  toggle(_event: unknown): void {}
}

@Component({ selector: 'p-button', standalone: true, template: '<ng-content />' })
class ButtonStub {}

describe('ShellComponent', () => {
  let fixture: ComponentFixture<ShellComponent>;
  let authSvc: AuthService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ShellComponent],
      providers: [
        provideRouter([]),
      ],
    })
    .overrideComponent(ShellComponent, {
      remove: { imports: [] },
    })
    .compileComponents();

    // Override PrimeNG component imports with stubs
    TestBed.overrideComponent(ShellComponent, {
      remove: { imports: [] },
    });

    fixture  = TestBed.createComponent(ShellComponent);
    authSvc  = TestBed.inject(AuthService);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render 4 nav items', () => {
    const items = fixture.nativeElement.querySelectorAll('.nav-item');
    expect(items.length).toBeGreaterThanOrEqual(4);
  });

  it('should show "U" initials when no user is set', () => {
    expect(fixture.componentInstance['userInitials']).toBe('U');
  });

  it('should show correct initials for logged-in user', () => {
    authSvc.setSession('tok', { id: 1, name: 'Mugunthan S', phone: '+91' });
    expect(fixture.componentInstance['userInitials']).toBe('MS');
  });

  it('userMenuItems should include Log out', () => {
    const items = fixture.componentInstance['userMenuItems'];
    const hasLogout = items.some((i: { label?: string }) => i.label === 'Log out');
    expect(hasLogout).toBe(true);
  });
});
