import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeFileUploadComponent } from './file-upload.component';

describe('MeeFileUploadComponent', () => {
  let fixture: ComponentFixture<MeeFileUploadComponent>;
  let comp: MeeFileUploadComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeFileUploadComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeFileUploadComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default accept to image/*', () => {
    expect(comp.accept()).toBe('image/*');
  });

  it('should compute max file size in bytes', () => {
    fixture.componentRef.setInput('max_size_mb', 10);
    expect(comp.maxFileSizeBytes()).toBe(10 * 1024 * 1024);
  });

  it('should emit files_selected on upload handler', () => {
    let emitted: File[] = [];
    comp.files_selected.subscribe((e) => { emitted = e.files; });
    const mockFile = new File(['content'], 'test.jpg', { type: 'image/jpeg' });
    comp.onUploadHandler({ files: [mockFile] });
    expect(emitted.length).toBe(1);
    expect(emitted[0].name).toBe('test.jpg');
  });

  it('should emit upload_error', () => {
    let emitted = '';
    comp.upload_error.subscribe((msg: string) => { emitted = msg; });
    comp.upload_error.emit('Upload failed');
    expect(emitted).toBe('Upload failed');
  });
});
