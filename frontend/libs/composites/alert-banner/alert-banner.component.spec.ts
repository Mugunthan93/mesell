import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MeeAlertBannerComponent, MeeAlertVariant } from './alert-banner.component';

async function createFixture(
  variant: MeeAlertVariant,
  message: string,
): Promise<ComponentFixture<MeeAlertBannerComponent>> {
  await TestBed.configureTestingModule({
    imports: [MeeAlertBannerComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(MeeAlertBannerComponent);
  fixture.componentRef.setInput('variant', variant);
  fixture.componentRef.setInput('message', message);
  fixture.detectChanges();
  return fixture;
}

describe('MeeAlertBannerComponent', () => {
  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('renders the message for error variant', async () => {
    const fixture = await createFixture('error', 'Something went wrong.');
    expect(fixture.nativeElement.textContent).toContain('Something went wrong.');
  });

  it('applies the error variant CSS class', async () => {
    const fixture = await createFixture('error', 'Error message');
    const banner = fixture.nativeElement.querySelector('.mee-alert-banner--error');
    expect(banner).toBeTruthy();
  });

  it('applies the warning variant CSS class', async () => {
    const fixture = await createFixture('warning', 'Warning message');
    const banner = fixture.nativeElement.querySelector('.mee-alert-banner--warning');
    expect(banner).toBeTruthy();
  });

  it('applies the info variant CSS class', async () => {
    const fixture = await createFixture('info', 'Info message');
    const banner = fixture.nativeElement.querySelector('.mee-alert-banner--info');
    expect(banner).toBeTruthy();
  });

  it('applies the success variant CSS class', async () => {
    const fixture = await createFixture('success', 'Success message');
    const banner = fixture.nativeElement.querySelector('.mee-alert-banner--success');
    expect(banner).toBeTruthy();
  });

  it('has role="alert" for immediate screen reader announcement', async () => {
    const fixture = await createFixture('error', 'Accessibility test');
    const el = fixture.nativeElement.querySelector('[role="alert"]');
    expect(el).toBeTruthy();
  });

  it('has aria-live="polite" on the banner element', async () => {
    const fixture = await createFixture('error', 'Accessibility test');
    const el = fixture.nativeElement.querySelector('[aria-live="polite"]');
    expect(el).toBeTruthy();
  });

  it('has tabindex="-1" for programmatic focus', async () => {
    const fixture = await createFixture('error', 'Focus test');
    const banner = fixture.nativeElement.querySelector('.mee-alert-banner');
    expect(banner?.getAttribute('tabindex')).toBe('-1');
  });

  it('icon char is "!" for error variant', async () => {
    const fixture = await createFixture('error', 'Error');
    expect(fixture.componentInstance.iconChar()).toBe('!');
  });

  it('icon char is "⚠" for warning variant', async () => {
    const fixture = await createFixture('warning', 'Warning');
    expect(fixture.componentInstance.iconChar()).toBe('⚠');
  });

  it('icon char is "i" for info variant', async () => {
    const fixture = await createFixture('info', 'Info');
    expect(fixture.componentInstance.iconChar()).toBe('i');
  });

  it('icon char is "✓" for success variant', async () => {
    const fixture = await createFixture('success', 'Done');
    expect(fixture.componentInstance.iconChar()).toBe('✓');
  });

  it('defaults to error variant when none supplied', async () => {
    await TestBed.configureTestingModule({
      imports: [MeeAlertBannerComponent],
    }).compileComponents();
    const f = TestBed.createComponent(MeeAlertBannerComponent);
    f.componentRef.setInput('message', 'Default variant test');
    f.detectChanges();
    expect(f.componentInstance.variant()).toBe('error');
  });
});
