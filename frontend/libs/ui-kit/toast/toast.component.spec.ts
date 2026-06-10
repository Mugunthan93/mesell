import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MessageService } from 'primeng/api';
import { MeeToastService } from './toast.service';
import { MeeToastComponent } from './toast.component';
import { ComponentFixture } from '@angular/core/testing';

describe('MeeToastComponent', () => {
  let fixture: ComponentFixture<MeeToastComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeToastComponent, NoopAnimationsModule],
      providers: [MessageService],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeToastComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });
});

describe('MeeToastService', () => {
  let service: MeeToastService;
  let msgSvc: MessageService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [MessageService, MeeToastService],
    });
    service = TestBed.inject(MeeToastService);
    msgSvc = TestBed.inject(MessageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should call msgSvc.add with success severity', () => {
    const spy = vi.spyOn(msgSvc, 'add');
    service.success('Saved!');
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'success', detail: 'Saved!' })
    );
  });

  it('should call msgSvc.add with error severity', () => {
    const spy = vi.spyOn(msgSvc, 'add');
    service.error('Failed!');
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'error', detail: 'Failed!' })
    );
  });

  it('should call msgSvc.add with warn severity', () => {
    const spy = vi.spyOn(msgSvc, 'add');
    service.warn('Heads up!');
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'warn', detail: 'Heads up!' })
    );
  });

  it('should call msgSvc.add with info severity', () => {
    const spy = vi.spyOn(msgSvc, 'add');
    service.info('Processing');
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'info', detail: 'Processing' })
    );
  });
});
