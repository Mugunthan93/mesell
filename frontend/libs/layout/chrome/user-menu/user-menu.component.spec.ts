import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeUserMenuComponent } from './user-menu.component';
import type { MeeMenuItem } from '@mesell/ui-kit';

const ITEMS: MeeMenuItem[] = [
  { label: 'My Profile', icon: 'user', routerLink: '/profile' },
  { separator: true },
  { label: 'Log out', icon: 'logout', command: () => {} },
];

describe('MeeUserMenuComponent', () => {
  let fixture: ComponentFixture<MeeUserMenuComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeUserMenuComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeUserMenuComponent);
    fixture.componentRef.setInput('initials', 'MS');
    fixture.componentRef.setInput('items', ITEMS);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render the avatar with the initials', () => {
    const avatar = fixture.nativeElement.querySelector('.avatar');
    expect(avatar).toBeTruthy();
    expect(avatar.textContent?.trim()).toBe('MS');
  });

  it('should expose an accessible avatar button', () => {
    const avatar = fixture.nativeElement.querySelector('.avatar');
    expect(avatar.getAttribute('role')).toBe('button');
    expect(avatar.getAttribute('tabindex')).toBe('0');
  });

  it('should toggle the menu without throwing', () => {
    const avatar = fixture.nativeElement.querySelector('.avatar');
    expect(() => avatar.click()).not.toThrow();
  });
});
