import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeToolbarComponent } from './toolbar.component';

describe('MeeToolbarComponent', () => {
  let fixture: ComponentFixture<MeeToolbarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeToolbarComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeToolbarComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render an inner flex container div', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div).toBeTruthy();
    expect(div.className).toContain('flex');
  });

  it('should apply justify-between for space-between layout', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('justify-between');
  });

  it('should apply items-center by default (align="center")', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('items-center');
  });

  it('should apply items-start when align is "start"', () => {
    fixture.componentRef.setInput('align', 'start');
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('items-start');
    expect(div.className).not.toContain('items-center');
  });

  it('should apply items-end when align is "end"', () => {
    fixture.componentRef.setInput('align', 'end');
    fixture.detectChanges();
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('items-end');
  });

  it('should include flex-wrap for mobile wrap behaviour', () => {
    const div = fixture.nativeElement.querySelector('div');
    expect(div.className).toContain('flex-wrap');
  });

  it('should bind sm gap token via [style.gap] by default (gap="sm")', () => {
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-2)');
  });

  it('should bind correct gap token for gap="md"', () => {
    fixture.componentRef.setInput('gap', 'md');
    fixture.detectChanges();
    const div: HTMLElement = fixture.nativeElement.querySelector('div');
    expect(div.style.gap).toBe('var(--mee-space-4)');
  });
});
