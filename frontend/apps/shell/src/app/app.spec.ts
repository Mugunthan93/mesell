import { TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { provideMeeUi } from '@mesell/ui-kit';
import { AppComponent } from './app';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent, RouterTestingModule],
      // AppComponent renders <mee-toast /> which wraps PrimeNG Toast.
      // PrimeNG Toast injects MessageService at component creation time.
      // At runtime this is provided by ...provideMeeUi() in app.config.ts;
      // the TestBed harness must mirror that exact provider set (FE-1 clean).
      providers: [...provideMeeUi()],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
