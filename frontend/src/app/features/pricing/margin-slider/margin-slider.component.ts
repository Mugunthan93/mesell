// features/pricing/margin-slider/margin-slider.component.ts
// Selector: mee-margin-slider
// MRP slider with debounced change + committed (API-trigger) outputs

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  OnInit,
  OnDestroy,
  inject,
  DestroyRef,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subject, debounceTime } from 'rxjs';
import { MatSliderModule } from '@angular/material/slider';
import { TranslocoModule } from '@jsverse/transloco';
import { InrCurrencyPipe } from '@shared/pipes/inr-currency.pipe';

@Component({
  selector: 'mee-margin-slider',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatSliderModule, TranslocoModule, InrCurrencyPipe],
  styles: [`
    :host { display: block; }
    .slider-wrap {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .slider-label {
      font-size: 13px;
      font-weight: 500;
      color: var(--mee-color-on-surface);
    }
    .slider-value {
      font-size: 20px;
      font-weight: 700;
      color: var(--mee-color-primary);
    }
    mat-slider {
      width: 100%;
    }
    .slider-range {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #9CA3AF;
      margin-top: -4px;
    }
  `],
  template: `
    <div class="slider-wrap" role="group" aria-label="MRP slider">
      <span class="slider-label">{{ 'pricing.mrp.label' | transloco }}</span>
      <span class="slider-value" aria-live="polite">{{ mrp() | inrCurrency }}</span>

      <mat-slider
        [min]="minMrp()"
        [max]="maxMrp()"
        [step]="1"
        [discrete]="true"
        aria-label="Maximum Retail Price"
      >
        <input
          matSliderThumb
          [value]="mrp()"
          (valueChange)="onValueChange($event)"
          (change)="onCommit($event)"
        />
      </mat-slider>

      <div class="slider-range" aria-hidden="true">
        <span>Min: {{ minMrp() | inrCurrency }}</span>
        <span>Max: {{ maxMrp() | inrCurrency }}</span>
      </div>
    </div>
  `,
})
export class MarginSliderComponent implements OnInit, OnDestroy {
  readonly mrp = input.required<number>();
  readonly minMrp = input<number>(50);
  readonly maxMrp = input<number>(10000);

  readonly mrpChanged = output<number>();
  readonly mrpCommitted = output<number>();

  private readonly destroyRef = inject(DestroyRef);
  private readonly changeSubject$ = new Subject<number>();

  ngOnInit(): void {
    // 100ms debounce for live display updates
    this.changeSubject$
      .pipe(debounceTime(100), takeUntilDestroyed(this.destroyRef))
      .subscribe((value) => {
        this.mrpChanged.emit(value);
      });
  }

  ngOnDestroy(): void {
    this.changeSubject$.complete();
  }

  onValueChange(value: number): void {
    this.changeSubject$.next(value);
  }

  onCommit(event: Event): void {
    const input = event.target as HTMLInputElement;
    const value = Number(input.value);
    if (!isNaN(value)) {
      // 500ms committed after slide end — fires the actual API call
      setTimeout(() => {
        this.mrpCommitted.emit(value);
      }, 500);
    }
  }
}
