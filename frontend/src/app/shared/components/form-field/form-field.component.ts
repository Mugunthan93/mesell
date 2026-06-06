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
      <label style="font-size:13px; font-weight:500; color:#374151; display:block; margin-bottom:6px;">
        {{ label() }}
        @if (required()) {
          <span aria-hidden="true" style="color:#DC2626; margin-left:2px;">*</span>
        }
      </label>

      <div class="mee-form-field__control">
        <ng-content />
      </div>

      @if (hint()) {
        <div class="mee-form-field__hint" style="font-size:12px; color:#6B7280; margin-top:4px;">
          {{ hint() }}
        </div>
      }

      @if (error()) {
        <div class="mee-form-field__error" role="alert" style="font-size:12px; color:#DC2626; font-weight:500; margin-top:4px;">
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
