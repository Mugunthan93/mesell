import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeDialogComponent } from './dialog.component';

describe('MeeDialogComponent', () => {
  let fixture: ComponentFixture<MeeDialogComponent>;
  let comp: MeeDialogComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeDialogComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeDialogComponent);
    comp = fixture.componentInstance;
    fixture.componentRef.setInput('header', 'Test Dialog');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default visible to false', () => {
    expect(comp.visible()).toBe(false);
  });

  it('should default width to 480px', () => {
    expect(comp.width()).toBe('480px');
  });

  it('should default closable to true', () => {
    expect(comp.closable()).toBe(true);
  });

  it('should emit visibleChange', () => {
    let emitted: boolean | null = null;
    comp.visibleChange.subscribe((v: boolean) => { emitted = v; });
    comp.visibleChange.emit(false);
    expect(emitted).toBe(false);
  });

  it('should emit closed', () => {
    let emitted = false;
    comp.closed.subscribe(() => { emitted = true; });
    comp.closed.emit();
    expect(emitted).toBe(true);
  });
});
