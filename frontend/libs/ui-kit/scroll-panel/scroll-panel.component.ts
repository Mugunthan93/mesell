/**
 * mee-scroll-panel — constrained scrollable region.
 *
 * PrimeNG ScrollPanel v21 does not accept a [style] input.
 * maxHeight is applied via a host wrapper div so the primitive
 * is properly constrained. styleClass is forwarded to p-scrollpanel.
 */
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { ScrollPanel } from 'primeng/scrollpanel';

@Component({
  selector: 'mee-scroll-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ScrollPanel],
  styles: [`:host { display: block; width: 100%; }`],
  template: `
    <div [style]="hostStyle()">
      <p-scrollpanel
        [styleClass]="styleClass()"
        style="width: 100%; height: 100%;"
      >
        <ng-content></ng-content>
      </p-scrollpanel>
    </div>
  `,
})
export class MeeScrollPanelComponent {
  /** Max height of the scroll region (CSS value, e.g. '300px', '50vh'). */
  readonly maxHeight  = input<string>('100%');
  /** Extra CSS class forwarded to p-scrollpanel's host. */
  readonly styleClass = input<string | undefined>(undefined);

  readonly hostStyle = computed<Record<string, string>>(() => ({
    height:    this.maxHeight(),
    maxHeight: this.maxHeight(),
    width:     '100%',
    overflow:  'hidden',
  }));
}
