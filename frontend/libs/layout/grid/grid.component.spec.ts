import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeGridComponent } from './grid.component';

describe('MeeGridComponent', () => {
  let fixture: ComponentFixture<MeeGridComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeGridComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeGridComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render an inner grid div', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div).toBeTruthy();
    expect(div.className).toContain('grid');
  });

  it('should project content via ng-content', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div).toBeTruthy();
  });

  it('should set gridTemplateColumns style in auto mode (default)', () => {
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gridTemplateColumns).toBe('repeat(auto-fill, minmax(16rem, 1fr))');
  });

  it('should use custom minItemWidth in auto mode', () => {
    fixture.componentRef.setInput('minItemWidth', '20rem');
    fixture.detectChanges();
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gridTemplateColumns).toBe('repeat(auto-fill, minmax(20rem, 1fr))');
  });

  it('should not set gridTemplateColumns inline when cols is numeric', () => {
    fixture.componentRef.setInput('cols', 3);
    fixture.detectChanges();
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    // computed returns null — Angular clears the style property
    expect(div.style.gridTemplateColumns).toBeFalsy();
  });

  it('should include Tailwind grid-cols class for cols=2', () => {
    fixture.componentRef.setInput('cols', 2);
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('grid-cols-1');
    expect(div.className).toContain('sm:grid-cols-2');
  });

  it('should include mobile-first grid-cols-1 for cols=3', () => {
    fixture.componentRef.setInput('cols', 3);
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('grid-cols-1');
  });

  it('should use lg:grid-cols-4 (not md:grid-cols-4) for cols=4 — tablet-friendly progression', () => {
    // Responsive fix: cols=4 uses sm:2 → md:3 → lg:4 rather than md:4.
    // Jumping directly from 2→4 cols at 768px leaves tablet users with
    // items that are too narrow. The md step gives 3 cols at 768–1023px.
    fixture.componentRef.setInput('cols', 4);
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('grid-cols-1');
    expect(div.className).toContain('sm:grid-cols-2');
    expect(div.className).toContain('md:grid-cols-3');
    expect(div.className).toContain('lg:grid-cols-4');
  });

  it('should bind gap token via [style.gap] for default md gap', () => {
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-4)');
  });

  it('should bind gap="xl" to var(--mee-space-8)', () => {
    fixture.componentRef.setInput('gap', 'xl');
    fixture.detectChanges();
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-8)');
  });
});
