// shared/directives/autosave.directive.ts
// Form autosave dispatcher per V1 §F3 — 10s + blur, with offline queue per §5.E.1

import {
  Directive,
  ElementRef,
  EventEmitter,
  inject,
  input,
  OnDestroy,
  OnInit,
  Output,
} from '@angular/core';
import { AbstractControl } from '@angular/forms';
import {
  debounceTime,
  distinctUntilChanged,
  filter,
  fromEvent,
  mergeMap,
  Observable,
  Subject,
  Subscription,
  switchMap,
  take,
  toArray,
} from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';
import { NetworkService } from '@core/services/network.service';

export type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error';

@Directive({
  selector: '[meeAutosave]',
  standalone: true,
})
export class AutosaveDirective implements OnInit, OnDestroy {
  // ── Inputs ──

  /** The persistence callback — typically calls apiClient.patch */
  readonly meeAutosave = input.required<(formValue: unknown) => Observable<void>>();

  /** Debounce before persisting after last change. Default: 10 000 ms (10s) */
  readonly meeAutosaveDebounceMs = input<number>(10_000);

  /** Whether to flush on blur of the host element. Default: true */
  readonly meeAutosaveOnBlur = input<boolean>(true);

  /** The FormGroup to watch — injected manually by host component */
  readonly meeAutosaveControl = input<AbstractControl | null>(null);

  // ── Outputs ──

  @Output() readonly meeAutosaveStatus = new EventEmitter<AutosaveStatus>();

  // ── DI ──

  private readonly el = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly network = inject(NetworkService);

  // ── Internal ──

  private readonly subs = new Subscription();
  private readonly pendingFlush$ = new Subject<unknown>();
  private savedTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    const control = this.meeAutosaveControl();

    if (control) {
      // Watch FormGroup.valueChanges with debounce
      this.subs.add(
        control.valueChanges.pipe(
          debounceTime(this.meeAutosaveDebounceMs()),
          distinctUntilChanged(),
        ).subscribe(value => this.enqueue(value)),
      );
    }

    if (this.meeAutosaveOnBlur()) {
      // Also flush on blur of any input inside the host
      this.subs.add(
        fromEvent(this.el.nativeElement, 'blur', { capture: true }).subscribe(() => {
          const value = control?.value;
          if (value !== undefined) this.enqueue(value);
        }),
      );
    }

    // Drain queue when connection is restored
    this.subs.add(
      toObservable(this.network.online).pipe(
        filter(online => online),
        switchMap(() => this.pendingFlush$.pipe(take(1))),
      ).subscribe(value => this.persist(value)),
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
    if (this.savedTimer !== null) clearTimeout(this.savedTimer);
  }

  private enqueue(value: unknown): void {
    if (!this.network.online()) {
      // Queue: emit into the pending stream; dequeued on reconnect
      this.pendingFlush$.next(value);
      return;
    }
    this.persist(value);
  }

  private persist(value: unknown): void {
    this.meeAutosaveStatus.emit('saving');
    this.subs.add(
      this.meeAutosave()(value).subscribe({
        next: () => {
          this.meeAutosaveStatus.emit('saved');
          if (this.savedTimer !== null) clearTimeout(this.savedTimer);
          this.savedTimer = setTimeout(() => this.meeAutosaveStatus.emit('idle'), 3000);
        },
        error: () => {
          this.meeAutosaveStatus.emit('error');
        },
      }),
    );
  }
}
