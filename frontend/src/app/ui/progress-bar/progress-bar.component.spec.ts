import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeProgressBarComponent } from './progress-bar.component';

describe('MeeProgressBarComponent', () => {
  let fixture: ComponentFixture<MeeProgressBarComponent>;
  let comp: MeeProgressBarComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeProgressBarComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeProgressBarComponent);
    comp = fixture.componentInstance;
    fixture.componentRef.setInput('value', 50);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default show_value to true', () => {
    expect(comp.show_value()).toBe(true);
  });

  it('should reflect the value input', () => {
    expect(comp.value()).toBe(50);
  });

  it('should accept a label', () => {
    fixture.componentRef.setInput('label', 'Upload progress');
    fixture.detectChanges();
    expect(comp.label()).toBe('Upload progress');
  });
});
