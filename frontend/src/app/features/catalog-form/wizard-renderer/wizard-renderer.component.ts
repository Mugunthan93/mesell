// features/catalog-form/wizard-renderer/wizard-renderer.component.ts
// B2: Multi-step wizard shell per §18.B
// Renders mat-stepper with one step per WizardStep, dispatches fields via mee-field-dispatcher.

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { FieldSchema } from '@core/models/field-schema.model';
import { LocaleMap } from '@core/models/locale-map.model';
import { LocaleLabelPipe } from '@shared/pipes/locale-label.pipe';
import { ValueChange } from '../primitives/primitive.contract';
import { FieldDispatcherComponent } from './field-dispatcher.component';

export interface WizardStep {
  readonly id: string;
  readonly title: LocaleMap;
  readonly fields: readonly FieldSchema[];
}

@Component({
  selector: 'mee-wizard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatStepperModule, MatButtonModule, LocaleLabelPipe, FieldDispatcherComponent],
  styles: [`
    .step-actions {
      display: flex;
      gap: 12px;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--mee-color-outline);
    }
    :host {
      display: block;
    }
  `],
  template: `
    <mat-stepper #stepper linear>
      @for (step of steps(); track step.id) {
        <mat-step [label]="step.title | localeLabel">
          @for (field of step.fields; track field.canonicalName) {
            <mee-field-dispatcher
              [schema]="field"
              [value]="model()[field.canonicalName]"
              [aiSuggestion]="aiSuggestions()[field.canonicalName] ?? null"
              [disabled]="false"
              (valueChange)="patch($event)"
            />
          }
          <div class="step-actions">
            @if (stepper.selectedIndex !== 0) {
              <button mat-button matStepperPrevious>Back</button>
            }
            @if (stepper.selectedIndex < stepper.steps.length - 1) {
              <button mat-raised-button color="primary" matStepperNext>Next</button>
            } @else {
              <button mat-raised-button color="primary" (click)="onSubmit()">Save &amp; Continue</button>
            }
          </div>
        </mat-step>
      }
    </mat-stepper>
  `,
})
export class WizardRendererComponent {
  readonly steps = input.required<WizardStep[]>();
  readonly model = input.required<Record<string, unknown>>();
  readonly aiSuggestions = input<Record<string, AiSuggestion>>({});

  readonly valueChange = output<ValueChange>();
  readonly submit = output<void>();

  patch(change: ValueChange): void {
    this.valueChange.emit(change);
  }

  onSubmit(): void {
    this.submit.emit();
  }
}
