import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeFormLayoutComponent } from './form-layout.component';

describe('MeeFormLayoutComponent', () => {
  let fixture: ComponentFixture<MeeFormLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeFormLayoutComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeFormLayoutComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render an inner flex column div', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div).toBeTruthy();
    expect(div.className).toContain('flex');
    expect(div.className).toContain('flex-col');
  });

  it('should project content via ng-content', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div).toBeTruthy();
  });

  it('should apply max-w-screen-sm by default (maxWidth="md")', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('max-w-screen-sm');
  });

  it('should apply max-w-none for maxWidth="full"', () => {
    fixture.componentRef.setInput('maxWidth', 'full');
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('max-w-none');
  });

  it('should apply max-w-sm for maxWidth="sm"', () => {
    fixture.componentRef.setInput('maxWidth', 'sm');
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('max-w-sm');
  });

  it('should include [&>*]:w-full to force full-width children', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('[&>*]:w-full');
  });

  it('should bind gap="lg" to var(--mee-space-6) by default', () => {
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-6)');
  });

  it('should bind gap="sm" to var(--mee-space-2)', () => {
    fixture.componentRef.setInput('gap', 'sm');
    fixture.detectChanges();
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-2)');
  });

  it('should bind gap="xl" to var(--mee-space-8)', () => {
    fixture.componentRef.setInput('gap', 'xl');
    fixture.detectChanges();
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-8)');
  });
});
