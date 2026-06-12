import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeSpinnerComponent } from './spinner.component';

describe('MeeSpinnerComponent', () => {
  let fixture: ComponentFixture<MeeSpinnerComponent>;
  let comp: MeeSpinnerComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeSpinnerComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeSpinnerComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('exposes role=status and aria-busy on the host wrapper', () => {
    const host: HTMLElement = fixture.nativeElement.querySelector('.mee-spinner-host');
    expect(host).toBeTruthy();
    expect(host.getAttribute('role')).toBe('status');
    expect(host.getAttribute('aria-busy')).toBe('true');
  });

  it('defaults to a "Loading" aria-label when no label is given', () => {
    const host: HTMLElement = fixture.nativeElement.querySelector('.mee-spinner-host');
    expect(host.getAttribute('aria-label')).toBe('Loading');
    // no sr-only span when no label supplied
    expect(fixture.nativeElement.querySelector('.mee-spinner-sr')).toBeNull();
  });

  it('uses the provided label as both aria-label and sr-only text', () => {
    fixture.componentRef.setInput('label', 'Loading catalogs');
    fixture.detectChanges();
    const host: HTMLElement = fixture.nativeElement.querySelector('.mee-spinner-host');
    expect(host.getAttribute('aria-label')).toBe('Loading catalogs');
    const sr: HTMLElement = fixture.nativeElement.querySelector('.mee-spinner-sr');
    expect(sr).toBeTruthy();
    expect(sr.textContent?.trim()).toBe('Loading catalogs');
  });

  it('defaults diameter to 40px and reflects it in dimensionStyle', () => {
    expect(comp.diameter()).toBe(40);
    expect(comp.dimensionStyle()).toEqual({ width: '40px', height: '40px' });
  });

  it('reflects a custom diameter in dimensionStyle', () => {
    fixture.componentRef.setInput('diameter', 24);
    fixture.detectChanges();
    expect(comp.dimensionStyle()).toEqual({ width: '24px', height: '24px' });
  });

  it('defaults strokeWidth to "4"', () => {
    expect(comp.strokeWidth()).toBe('4');
  });

  it('renders the underlying PrimeNG progress spinner', () => {
    const spinner = fixture.nativeElement.querySelector('p-progress-spinner');
    expect(spinner).toBeTruthy();
    // decorative — hidden from the a11y tree (the host wrapper carries role=status)
    expect(spinner.getAttribute('aria-hidden')).toBe('true');
  });
});
