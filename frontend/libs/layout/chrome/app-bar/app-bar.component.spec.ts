import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeAppBarComponent } from './app-bar.component';

@Component({
  standalone: true,
  imports: [MeeAppBarComponent],
  template: `<mee-app-bar><span class="projected-action">Action</span></mee-app-bar>`,
})
class AppBarHostComponent {}

describe('MeeAppBarComponent', () => {
  let fixture: ComponentFixture<MeeAppBarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeAppBarComponent, AppBarHostComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeAppBarComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render a sticky .shell-header with a hamburger and spacer', () => {
    expect(fixture.nativeElement.querySelector('header.shell-header')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('.hamburger')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('.header-spacer')).toBeTruthy();
  });

  it('should emit menuToggle when the hamburger is clicked', () => {
    let emitted = false;
    fixture.componentInstance.menuToggle.subscribe(() => (emitted = true));
    fixture.nativeElement.querySelector('.hamburger').click();
    expect(emitted).toBe(true);
  });

  it('should project trailing actions content', () => {
    const host = TestBed.createComponent(AppBarHostComponent);
    host.detectChanges();
    expect(host.nativeElement.querySelector('.projected-action')?.textContent).toContain('Action');
  });
});
