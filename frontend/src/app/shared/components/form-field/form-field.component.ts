// shared/components/form-field/form-field.component.ts

import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'mee-form-field',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; }
  `],
  template: `
    <div class="mee-form-field">
      <label class="text-[13px] font-medium text-on-surface block mb-1.5">
        {{ label() }}
        @if (required()) {
          <span aria-hidden="true" class="text-error ml-0.5">*</span>
        }
      </label>

      <div class="mee-form-field__control">
        <ng-content />
      </div>

      @if (hint()) {
        <div class="mee-form-field__hint text-xs text-on-surface-variant mt-1">
          {{ hint() }}
        </div>
      }

      @if (error()) {
        <div class="mee-form-field__error text-xs text-error font-medium mt-1" role="alert">
          {{ error() }}
        </div>
      }
    </div>
  `,
})
export class FormFieldComponent {
  readonly label = input.required<string>();
  readonly hint = input<string | undefined>(undefined);
  readonly error = input<string | undefined>(undefined);
  readonly required = input<boolean>(false);
}
