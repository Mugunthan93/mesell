import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeStackComponent } from './stack.component';

describe('MeeStackComponent', () => {
  let fixture: ComponentFixture<MeeStackComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeStackComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeStackComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render an inner flex div', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div).toBeTruthy();
    expect(div.className).toContain('flex');
  });

  it('should project content via ng-content', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div).toBeTruthy();
  });

  it('should default to flex-col (direction="vertical")', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('flex-col');
  });

  it('should apply flex-row for direction="horizontal"', () => {
    fixture.componentRef.setInput('direction', 'horizontal');
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('flex-row');
    expect(div.className).not.toContain('flex-col');
  });

  it('should apply items-stretch by default (align="stretch")', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('items-stretch');
  });

  it('should apply items-center for align="center"', () => {
    fixture.componentRef.setInput('align', 'center');
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('items-center');
  });

  it('should apply justify-start by default', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('justify-start');
  });

  it('should apply justify-between for justify="between"', () => {
    fixture.componentRef.setInput('justify', 'between');
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('justify-between');
  });

  it('should apply flex-nowrap by default (wrap=false)', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('flex-nowrap');
  });

  it('should apply flex-wrap when wrap=true', () => {
    fixture.componentRef.setInput('wrap', true);
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('flex-wrap');
    expect(div.className).not.toContain('flex-nowrap');
  });

  it('should bind gap="md" to var(--mee-space-4) via [style.gap]', () => {
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-4)');
  });

  it('should bind gap="lg" to var(--mee-space-6)', () => {
    fixture.componentRef.setInput('gap', 'lg');
    fixture.detectChanges();
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-6)');
  });

  it('should bind gap="xs" to var(--mee-space-1)', () => {
    fixture.componentRef.setInput('gap', 'xs');
    fixture.detectChanges();
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-1)');
  });
});
