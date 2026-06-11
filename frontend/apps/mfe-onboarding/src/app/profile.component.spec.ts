import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { Router } from '@angular/router';
import { ProfileComponent } from './profile.component';
import { AuthService, AuthUser } from '@mesell/core';

function makeAuthUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return { id: 1, name: 'Mugunthan', phone: '+919876543210', ...overrides };
}

describe('ProfileComponent', () => {
  let fixture: ComponentFixture<ProfileComponent>;
  let comp: ProfileComponent;
  let authService: AuthService;
  let router: Router;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        ProfileComponent,
        ReactiveFormsModule,
      ],
      providers: [
        provideRouter([]),
        provideAnimationsAsync('noop'),
      ],
    }).compileComponents();

    authService = TestBed.inject(AuthService);
    router = TestBed.inject(Router);

    // Seed a logged-in session
    authService.setSession('fake-token', makeAuthUser());

    fixture = TestBed.createComponent(ProfileComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // --- Gate 1: Component creation + form initialisation ---
  it('should create without errors', () => {
    expect(comp).toBeTruthy();
  });

  it('should initialise the name field from currentUser on init', () => {
    const nameValue = comp.form.get('name')?.value;
    expect(nameValue).toBe('Mugunthan');
  });

  it('should have a valid form when name is populated on init', () => {
    expect(comp.form.valid).toBeTruthy();
  });

  // --- Gate 2: Save button disabled when name is empty or invalid ---
  it('should report form invalid when name is empty', () => {
    comp.form.get('name')!.setValue('');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should report form invalid when name is 1 character (minLength=2)', () => {
    comp.form.get('name')!.setValue('A');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should report form valid when name meets requirements', () => {
    comp.form.get('name')!.setValue('AB');
    fixture.detectChanges();
    expect(comp.form.valid).toBeTruthy();
  });

  it('should show nameError when name is touched and empty', () => {
    comp.form.get('name')!.setValue('');
    comp.form.get('name')!.markAsTouched();
    comp.form.get('name')!.markAsDirty();
    fixture.detectChanges();
    expect(comp.nameError()).toBe('Name is required');
  });

  // --- Gate 3: Log out calls auth.logout() ---
  it('should call auth.logout() and navigate to /login on onLogout()', async () => {
    const logoutSpy = vi.spyOn(authService, 'logout');
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    await comp.onLogout();

    expect(logoutSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  // --- Computed signal tests ---
  it('should strip +91 prefix in displayPhone()', () => {
    expect(comp.displayPhone()).toBe('9876543210');
  });

  it('should format phone with spaces in formattedPhone()', () => {
    expect(comp.formattedPhone()).toBe('+91 98765 43210');
  });

  it('should derive avatarInitial from the user name', () => {
    expect(comp.avatarInitial()).toBe('M');
  });

  it('should use S as avatarInitial fallback when name is empty', () => {
    authService.setSession('fake-token', makeAuthUser({ name: '' }));
    expect(comp.avatarInitial()).toBe('S');
  });

  it('should compute planSeverity as neutral (Free plan)', () => {
    expect(comp.planSeverity()).toBe('neutral');
  });

  it('should compute planLabel as Free plan', () => {
    expect(comp.planLabel()).toBe('Free plan');
  });

  // --- Save simulation ---
  it('should set saving=true then saving=false after simulated save', () => {
    vi.useFakeTimers();

    comp.form.get('name')!.setValue('Test Name');
    fixture.detectChanges();

    comp.onSubmit();
    expect(comp.saving()).toBeTruthy();

    vi.advanceTimersByTime(800);
    expect(comp.saving()).toBeFalsy();
    expect(comp.saved()).toBeTruthy();

    vi.advanceTimersByTime(3000);
    expect(comp.saved()).toBeFalsy();

    vi.useRealTimers();
  });

  it('should not submit when form is invalid', () => {
    comp.form.get('name')!.setValue('');
    comp.onSubmit();
    expect(comp.saving()).toBeFalsy();
  });
});
