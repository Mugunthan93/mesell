/**
 * mee-panel — collapsible panel surface.
 *
 * Border-radius 16px is already in MeeSellPreset components.panel.root —
 * no CSS override needed here.
 *
 * PrimeNG Panel.collapsed is a classic @Input (booleanAttribute), not a signal.
 * PrimeNG emits collapsedChange EventEmitter on toggle. mee-panel exposes
 * a model<boolean>() for two-way binding on the consumer side.
 *
 * Template naming note: the <ng-template #headerTpl> avoids the name clash
 * between the PrimeNG query name "header" and our `header()` signal input.
 * The template is used to inject the icon into the panel header area.
 *
 * Panel.collapsedChange emits `boolean | undefined` in PrimeNG v21 — the
 * handler normalises undefined to false.
 */
import {
  ChangeDetectionStrategy,
  Component,
  input,
  model,
  output,
} from '@angular/core';
import { Panel } from 'primeng/panel';
import { resolveIcon } from '../icon/icon.registry';
import type { MeeIconName } from '../icon/icon.registry';

@Component({
  selector: 'mee-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Panel],
  template: `
    @if (icon()) {
      <!-- Panel with custom header template to show icon + text -->
      <p-panel
        [toggleable]="toggleable()"
        [collapsed]="collapsed()"
        (collapsedChange)="onCollapsedChange($event)"
      >
        <ng-template #header>
          <span class="flex items-center gap-2">
            <i [class]="resolveIcon(icon()!)" aria-hidden="true"></i>
            @if (panelHeader()) { <span>{{ panelHeader() }}</span> }
          </span>
        </ng-template>
        <ng-content></ng-content>
      </p-panel>
    } @else {
      <!-- Panel with plain text header -->
      <p-panel
        [header]="panelHeader()"
        [toggleable]="toggleable()"
        [collapsed]="collapsed()"
        (collapsedChange)="onCollapsedChange($event)"
      >
        <ng-content></ng-content>
      </p-panel>
    }
  `,
})
export class MeePanelComponent {
  /** Panel header text. Named panelHeader internally to avoid ng-template name collision. */
  readonly panelHeader = input<string | undefined>(undefined, { alias: 'header' });
  readonly toggleable  = input<boolean>(false);
  readonly collapsed   = model<boolean>(false);
  readonly icon        = input<MeeIconName | undefined>(undefined);

  /** Emits the new collapsed state after toggle. */
  readonly toggled = output<boolean>();

  readonly resolveIcon = resolveIcon;

  onCollapsedChange(value: boolean | undefined): void {
    const next = value ?? false;
    this.collapsed.set(next);
    this.toggled.emit(next);
  }
}
