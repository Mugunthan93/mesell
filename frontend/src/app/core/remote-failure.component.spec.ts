import { describe, it, expect, beforeEach } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RemoteFailureComponent } from './remote-failure.component';

describe('RemoteFailureComponent (MF Sub-Plan 01 — D12 error boundary)', () => {
  let fixture: ComponentFixture<RemoteFailureComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RemoteFailureComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(RemoteFailureComponent);
    fixture.detectChanges();
  });

  it('creates', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('renders a mee-empty-state with an unavailable message', () => {
    const el: HTMLElement = fixture.nativeElement;
    const emptyState = el.querySelector('mee-empty-state');
    expect(emptyState).toBeTruthy();
    expect(el.textContent).toContain('temporarily unavailable');
  });
});
