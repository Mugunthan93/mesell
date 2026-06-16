import { TestBed } from '@angular/core/testing';
import { MeeIconComponent } from './icon.component';
import { MEE_ICONS } from './icon.registry';

describe('MeeIconComponent', () => {
  function makeComp(name: keyof typeof MEE_ICONS): MeeIconComponent {
    const fixture = TestBed.createComponent(MeeIconComponent);
    fixture.componentRef.setInput('name', name);
    // Do NOT call detectChanges — avoids PrimeNG jsdom rendering issues
    return fixture.componentInstance;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeIconComponent],
    }).compileComponents();
  });

  it('should create', () => {
    const comp = makeComp('dashboard');
    expect(comp).toBeTruthy();
  });

  it('name="dashboard" resolves to MEE_ICONS["dashboard"]', () => {
    const comp = makeComp('dashboard');
    // Assert against the registry constant — no icon class literal in this spec
    expect(comp.resolved()).toBe(MEE_ICONS['dashboard']);
  });

  it('name="send" resolves to MEE_ICONS["send"]', () => {
    const comp = makeComp('send');
    expect(comp.resolved()).toBe(MEE_ICONS['send']);
  });

  it('name="menu" resolves to MEE_ICONS["menu"]', () => {
    const comp = makeComp('menu');
    expect(comp.resolved()).toBe(MEE_ICONS['menu']);
  });

  it('name="sparkles" resolves to MEE_ICONS["sparkles"]', () => {
    const comp = makeComp('sparkles');
    expect(comp.resolved()).toBe(MEE_ICONS['sparkles']);
  });

  it('name="warning" resolves to MEE_ICONS["warning"]', () => {
    const comp = makeComp('warning');
    expect(comp.resolved()).toBe(MEE_ICONS['warning']);
  });

  it('name="add" resolves to MEE_ICONS["add"]', () => {
    const comp = makeComp('add');
    expect(comp.resolved()).toBe(MEE_ICONS['add']);
  });
});
