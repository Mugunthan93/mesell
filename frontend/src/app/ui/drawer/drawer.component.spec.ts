import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeDrawerComponent } from './drawer.component';

describe('MeeDrawerComponent', () => {
  let fixture: ComponentFixture<MeeDrawerComponent>;
  let comp: MeeDrawerComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeDrawerComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeDrawerComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default visible to false', () => {
    expect(comp.visible()).toBe(false);
  });

  it('should default modal to true', () => {
    expect(comp.modal()).toBe(true);
  });

  it('should default styleClass to empty string', () => {
    expect(comp.styleClass()).toBe('');
  });

  it('should update visible via the model', () => {
    comp.visible.set(true);
    expect(comp.visible()).toBe(true);
  });
});
