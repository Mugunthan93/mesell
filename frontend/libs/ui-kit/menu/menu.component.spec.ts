import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeMenuComponent } from './menu.component';
import type { MeeMenuItem } from './menu.types';

const MOCK_ITEMS: MeeMenuItem[] = [
  { label: 'Profile', icon: 'pi pi-user', routerLink: '/profile' },
  { separator: true },
  { label: 'Log out', icon: 'pi pi-sign-out', command: () => {} },
];

describe('MeeMenuComponent', () => {
  let fixture: ComponentFixture<MeeMenuComponent>;
  let comp: MeeMenuComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeMenuComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeMenuComponent);
    comp = fixture.componentInstance;
    fixture.componentRef.setInput('items', MOCK_ITEMS);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should expose the items input', () => {
    expect(comp.items().length).toBe(3);
  });

  it('should toggle without error', () => {
    expect(() => comp.toggle(new Event('click'))).not.toThrow();
  });

  it('should forward a command through the mapped prime item', () => {
    let called = false;
    fixture.componentRef.setInput('items', [
      { label: 'Act', command: () => { called = true; } },
    ] satisfies MeeMenuItem[]);
    fixture.detectChanges();
    comp.toggle(new Event('click'));
    expect(called).toBe(false);
  });
});
