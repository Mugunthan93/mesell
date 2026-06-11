import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { Steps } from 'primeng/steps';
import type { MenuItem } from 'primeng/api';
import type { MeeStep } from './steps.types';

@Component({
  selector: 'mee-steps',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Steps],
  template: `
    <p-steps
      [model]="menuItems()"
      [activeIndex]="active_index()"
      [readonly]="false"
      (activeIndexChange)="active_index_change.emit($event)"
    />
  `,
})
export class MeeStepsComponent {
  readonly steps = input.required<MeeStep[]>();
  readonly active_index = input<number>(0);

  readonly active_index_change = output<number>();

  readonly menuItems = computed<MenuItem[]>(() =>
    this.steps().map((s) => ({
      label: s.label,
      ...(s.route ? { routerLink: s.route } : {}),
    }))
  );
}
