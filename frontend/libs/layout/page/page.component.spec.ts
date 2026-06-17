import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeePageComponent } from './page.component';

describe('MeePageComponent', () => {
  let fixture: ComponentFixture<MeePageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeePageComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeePageComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render a <div> container for content projection (not <main> — shell owns the main landmark)', () => {
    // mee-page renders a <div>, NOT a <main>. The Phase-4 shell wraps
    // <router-outlet> in its own <main class="page-content">, so a second
    // <main> inside mee-page would be a duplicate ARIA landmark (WCAG 2.4.1).
    const container = fixture.nativeElement.querySelector('div');
    expect(container).toBeTruthy();
    // Confirm no <main> is rendered (would be a duplicate landmark with the shell).
    expect(fixture.nativeElement.querySelector('main')).toBeNull();
  });

  it('should apply max-w-screen-lg class by default', () => {
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).toContain('max-w-screen-lg');
  });

  it('should apply max-w-screen-md when maxWidth is "md"', () => {
    fixture.componentRef.setInput('maxWidth', 'md');
    fixture.detectChanges();
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).toContain('max-w-screen-md');
  });

  it('should apply max-w-none when maxWidth is "full"', () => {
    fixture.componentRef.setInput('maxWidth', 'full');
    fixture.detectChanges();
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).toContain('max-w-none');
  });

  it('should include padding classes when padding is true (default)', () => {
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).toContain('px-4');
  });

  it('should omit padding classes when padding is false', () => {
    fixture.componentRef.setInput('padding', false);
    fixture.detectChanges();
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).not.toContain('px-4');
  });

  // --- Phase 6a: MeePagePadding scale tests (additive — back-compat tests above are UNCHANGED) ---

  it('should include lg:px-8 when padding is true (pins the default explicitly)', () => {
    fixture.componentRef.setInput('padding', true);
    fixture.detectChanges();
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).toContain('lg:px-8');
  });

  it('should apply full default padding when padding is "default" (≡ true)', () => {
    fixture.componentRef.setInput('padding', 'default');
    fixture.detectChanges();
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).toContain('px-4');
    expect(container.className).toContain('py-6');
    expect(container.className).toContain('sm:px-6');
    expect(container.className).toContain('lg:px-8');
  });

  it('should apply tight padding (px-4 py-6 sm:px-6) but NOT lg:px-8 when padding is "tight"', () => {
    fixture.componentRef.setInput('padding', 'tight');
    fixture.detectChanges();
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).toContain('px-4');
    expect(container.className).toContain('py-6');
    expect(container.className).toContain('sm:px-6');
    expect(container.className).not.toContain('lg:px-8');
  });

  it('should omit padding classes when padding is "none" (≡ false)', () => {
    fixture.componentRef.setInput('padding', 'none');
    fixture.detectChanges();
    const container = fixture.nativeElement.querySelector('div');
    expect(container.className).not.toContain('px-4');
    expect(container.className).not.toContain('lg:px-8');
  });

  it('should bind gap token via [style.gap] for gap="lg"', () => {
    fixture.componentRef.setInput('gap', 'lg');
    fixture.detectChanges();
    const container: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(container.style.gap).toBe('var(--mee-space-6)');
  });

  it('should bind gap token via [style.gap] for gap="sm"', () => {
    fixture.componentRef.setInput('gap', 'sm');
    fixture.detectChanges();
    const container: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(container.style.gap).toBe('var(--mee-space-2)');
  });

  it('should render 0 gap when gap is "none"', () => {
    fixture.componentRef.setInput('gap', 'none');
    fixture.detectChanges();
    const container: HTMLElement = fixture.nativeElement.querySelector('div');
    // Browser normalises '0' to '0px' for gap; check either form.
    expect(['0', '0px']).toContain(container.style.gap);
  });
});
