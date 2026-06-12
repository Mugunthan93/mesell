import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { MeeOfflineBannerComponent } from './offline-banner.component';
import { NetworkService } from '@mesell/core';

// Helper to create a fresh fixture with the given online state
async function createFixture(onlineState: boolean): Promise<ComponentFixture<MeeOfflineBannerComponent>> {
  const _online = signal(onlineState);
  const mockNetworkService: Pick<NetworkService, 'online'> = {
    online: _online.asReadonly(),
  };

  await TestBed.configureTestingModule({
    imports: [MeeOfflineBannerComponent],
    providers: [
      { provide: NetworkService, useValue: mockNetworkService },
    ],
  }).compileComponents();

  const fixture = TestBed.createComponent(MeeOfflineBannerComponent);
  fixture.detectChanges();
  return fixture;
}

describe('MeeOfflineBannerComponent', () => {
  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('should create', async () => {
    const fixture = await createFixture(true);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('does NOT show offline text when online is true', async () => {
    const fixture = await createFixture(true);
    const text = fixture.nativeElement.textContent ?? '';
    expect(text).not.toContain('offline');
  });

  it('shows offline message when online is false', async () => {
    const fixture = await createFixture(false);
    const text = fixture.nativeElement.textContent ?? '';
    expect(text.toLowerCase()).toContain('offline');
  });

  it('has role="status" on the banner container', async () => {
    const fixture = await createFixture(true);
    const el = fixture.nativeElement.querySelector('[role="status"]');
    expect(el).toBeTruthy();
  });

  it('has aria-live="polite" on the banner container', async () => {
    const fixture = await createFixture(true);
    const el = fixture.nativeElement.querySelector('[aria-live="polite"]');
    expect(el).toBeTruthy();
  });

  it('has aria-atomic="true" on the banner container', async () => {
    const fixture = await createFixture(true);
    const el = fixture.nativeElement.querySelector('[aria-atomic="true"]');
    expect(el).toBeTruthy();
  });

  it('sets aria-hidden="true" when online', async () => {
    const fixture = await createFixture(true);
    const el = fixture.nativeElement.querySelector('.mee-offline-banner');
    expect(el?.getAttribute('aria-hidden')).toBe('true');
  });

  it('sets aria-hidden="false" when offline', async () => {
    const fixture = await createFixture(false);
    const el = fixture.nativeElement.querySelector('.mee-offline-banner');
    expect(el?.getAttribute('aria-hidden')).toBe('false');
  });
});
