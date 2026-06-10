import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ConfirmationService } from 'primeng/api';
import { MeeConfirmDialogComponent, MeeConfirmService } from './confirm-dialog.component';
import { ComponentFixture } from '@angular/core/testing';

describe('MeeConfirmDialogComponent', () => {
  let fixture: ComponentFixture<MeeConfirmDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeConfirmDialogComponent, NoopAnimationsModule],
      providers: [ConfirmationService],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeConfirmDialogComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });
});

describe('MeeConfirmService', () => {
  let service: MeeConfirmService;
  let confirmSvc: ConfirmationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ConfirmationService, MeeConfirmService],
    });
    service = TestBed.inject(MeeConfirmService);
    confirmSvc = TestBed.inject(ConfirmationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should call ConfirmationService.confirm with message', () => {
    const spy = vi.spyOn(confirmSvc, 'confirm');
    const acceptFn = vi.fn();
    service.confirm({ message: 'Are you sure?', accept: acceptFn });
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Are you sure?' })
    );
  });

  it('should pass default header when none provided', () => {
    const spy = vi.spyOn(confirmSvc, 'confirm');
    service.confirm({ message: 'Delete?', accept: vi.fn() });
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ header: 'Confirm' })
    );
  });

  it('should pass custom header when provided', () => {
    const spy = vi.spyOn(confirmSvc, 'confirm');
    service.confirm({ message: 'Delete?', header: 'Delete Item', accept: vi.fn() });
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ header: 'Delete Item' })
    );
  });
});
