import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { Button } from 'primeng/button';
import type { MeeButtonVariant, MeeButtonSize } from './button.types';

@Component({
  selector: 'mee-button',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Button],
  template: `
    <p-button
      [label]="label()"
      [loading]="loading()"
      [disabled]="disabled()"
      [fluid]="fullWidth()"
      [severity]="pgSeverity()"
      [variant]="pgVariant()"
      [size]="pgSize()"
      [icon]="pgIcon()"
      [style]="{ minHeight: '44px' }"
      (onClick)="clicked.emit()"
    />
  `,
})
export class MeeButtonComponent {
  readonly label = input.required<string>();
  readonly variant = input<MeeButtonVariant>('primary');
  readonly size = input<MeeButtonSize>('md');
  readonly loading = input<boolean>(false);
  readonly disabled = input<boolean>(false);
  readonly fullWidth = input<boolean>(false);
  readonly icon = input<string | undefined>(undefined);

  readonly clicked = output<void>();

  readonly pgSeverity = computed(() => {
    const v = this.variant();
    switch (v) {
      case 'secondary': return 'secondary' as const;
      case 'ghost':     return 'contrast' as const;
      case 'danger':    return 'danger' as const;
      default:          return undefined;
    }
  });

  readonly pgVariant = computed(() => {
    const v = this.variant();
    if (v === 'ghost') return 'text' as const;
    if (v === 'secondary') return 'outlined' as const;
    return undefined;
  });

  readonly pgSize = computed(() => {
    const s = this.size();
    if (s === 'sm') return 'small' as const;
    if (s === 'lg') return 'large' as const;
    return undefined;
  });

  readonly pgIcon = computed(() => {
    const i = this.icon();
    if (!i) return undefined;
    // Accept Material Symbol names as-is — PrimeNG icon string passthrough
    return i;
  });
}
