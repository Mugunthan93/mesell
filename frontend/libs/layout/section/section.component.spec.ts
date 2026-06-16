import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeSectionComponent } from './section.component';

describe('MeeSectionComponent', () => {
  let fixture: ComponentFixture<MeeSectionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeSectionComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeSectionComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should project content via ng-content', () => {
    // body div is always present
    const bodyDiv = fixture.nativeElement.querySelector('div[style]');
    expect(bodyDiv).toBeTruthy();
  });

  it('should NOT render <h2> when heading is not set (default)', () => {
    expect(fixture.nativeElement.querySelector('h2')).toBeNull();
  });

  it('should render <h2> with heading text when heading input is set', () => {
    fixture.componentRef.setInput('heading', 'Recent catalogs');
    fixture.detectChanges();
    const h2 = fixture.nativeElement.querySelector('h2');
    expect(h2).toBeTruthy();
    expect(h2.textContent.trim()).toBe('Recent catalogs');
  });

  it('should NOT render <p> when description is not set', () => {
    fixture.componentRef.setInput('heading', 'Title');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('p')).toBeNull();
  });

  it('should render <p> when description is set', () => {
    fixture.componentRef.setInput('heading', 'Title');
    fixture.componentRef.setInput('description', 'Some detail');
    fixture.detectChanges();
    const p = fixture.nativeElement.querySelector('p');
    expect(p).toBeTruthy();
    expect(p.textContent.trim()).toBe('Some detail');
  });

  it('should apply gap token to body margin-top via [style.margin-top] when header exists', () => {
    fixture.componentRef.setInput('heading', 'Title');
    fixture.componentRef.setInput('gap', 'lg');
    fixture.detectChanges();
    const bodyDiv: HTMLElement = fixture.nativeElement.querySelector('div[style]');
    expect(bodyDiv.style.marginTop).toBe('var(--mee-space-6)');
  });

  it('should set margin-top 0 when no heading or description', () => {
    fixture.componentRef.setInput('gap', 'lg');
    fixture.detectChanges();
    const bodyDiv: HTMLElement = fixture.nativeElement.querySelector('div[style]');
    // Browser normalises '0' to '0px' for margin-top; check either form.
    expect(['0', '0px']).toContain(bodyDiv.style.marginTop);
  });
});
