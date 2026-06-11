import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeCardComponent } from './card.component';

describe('MeeCardComponent', () => {
  let fixture: ComponentFixture<MeeCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeCardComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeCardComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render a p-card element', () => {
    expect(fixture.nativeElement.querySelector('p-card')).toBeTruthy();
  });
});
