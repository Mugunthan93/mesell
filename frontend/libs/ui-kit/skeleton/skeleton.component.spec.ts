import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeSkeletonComponent } from './skeleton.component';

describe('MeeSkeletonComponent', () => {
  let fixture: ComponentFixture<MeeSkeletonComponent>;
  let comp: MeeSkeletonComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeSkeletonComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeSkeletonComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default variant to text', () => {
    expect(comp.variant()).toBe('text');
  });

  it('should default lines to 1', () => {
    expect(comp.lines()).toBe(1);
  });

  it('should accept card variant', () => {
    fixture.componentRef.setInput('variant', 'card');
    fixture.detectChanges();
    expect(comp.variant()).toBe('card');
  });

  it('should accept table-row variant', () => {
    fixture.componentRef.setInput('variant', 'table-row');
    fixture.detectChanges();
    expect(comp.variant()).toBe('table-row');
  });
});
