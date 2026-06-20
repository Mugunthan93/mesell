/**
 * mee-tabs — declarative-header + projected-body tab wrapper.
 *
 * Consumer supplies:
 *   [tabs]="tabDefs"        — header definitions (MeeTab[])
 *   [(value)]="activeTab"   — two-way active tab key (string | number)
 *   [scrollable]="true"     — optional scrollable tab list
 *
 * Content projection shape (consumer writes inside <mee-tabs>):
 *   <p-tabpanel value="tab1-key">Tab 1 body here.</p-tabpanel>
 *   <p-tabpanel value="tab2-key">Tab 2 body here.</p-tabpanel>
 *
 * Projection ends up inside <p-tabpanels> which mee-tabs renders.
 *
 * Note: p-tabs.value is a signal input with output valueChange in PrimeNG v21.
 *       [(value)] two-way binding is NOT available on signal inputs in Angular 18
 *       templates without a model(). Use [value] + (valueChange) instead.
 */
import {
  ChangeDetectionStrategy,
  Component,
  input,
  model,
  output,
} from '@angular/core';
import { Tabs, TabList, Tab, TabPanels } from 'primeng/tabs';
import { resolveIcon } from '../icon/icon.registry';
import type { MeeTab } from './tabs.types';

@Component({
  selector: 'mee-tabs',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Tabs, TabList, Tab, TabPanels],
  template: `
    <p-tabs
      [value]="value()"
      [scrollable]="scrollable()"
      (valueChange)="onTabChange($event)"
    >
      <p-tablist>
        @for (t of tabs(); track t.value) {
          <p-tab [value]="t.value" [disabled]="t.disabled ?? false">
            @if (t.icon) {
              <i [class]="resolveIcon(t.icon) + ' mr-2'" aria-hidden="true"></i>
            }
            {{ t.label }}
          </p-tab>
        }
      </p-tablist>
      <p-tabpanels>
        <ng-content></ng-content>
      </p-tabpanels>
    </p-tabs>
  `,
})
export class MeeTabsComponent {
  /** Header definitions for each tab. */
  readonly tabs       = input.required<MeeTab[]>();
  /** Two-way active tab key. Defaults to first tab's value when tabs are provided. */
  readonly value      = model<string | number>(0);
  /** Scrollable tab list (for many tabs on small screens). */
  readonly scrollable = input<boolean>(false);

  /** Emits the newly active tab value on selection change. */
  readonly tabChange = output<string | number>();

  readonly resolveIcon = resolveIcon;

  onTabChange(newValue: string | number | undefined): void {
    if (newValue !== undefined) {
      this.value.set(newValue);
      this.tabChange.emit(newValue);
    }
  }
}
