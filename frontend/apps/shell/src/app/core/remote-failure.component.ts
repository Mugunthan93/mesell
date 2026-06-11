import { ChangeDetectionStrategy, Component } from '@angular/core';
import { EmptyStateComponent } from '@mesell/composites';

/**
 * MF Sub-Plan 01 (D12 / MASTER_PLAN §6.4 failure-mode 1).
 *
 * Shell-owned error boundary for a federated remote that fails to load
 * (remoteEntry.json 404, network error, or a malformed manifest URL).
 * Rendered IN PLACE of the remote component so the user sees a graceful
 * "module unavailable" state instead of a white screen.
 *
 * Authored ONCE in the pilot and reused by every later remote (SP02–06)
 * via the `loadRemoteWithFallback` helper in `./load-remote`.
 */
@Component({
  selector: 'app-remote-failure',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EmptyStateComponent],
  template: `
    <mee-empty-state
      icon="cloud_off"
      message="This module is temporarily unavailable. Please retry in a moment."
      cta_label="Retry"
      (cta_click)="reload()"
    />
  `,
})
export class RemoteFailureComponent {
  /** Re-attempt the load by reloading the route (simplest robust recovery for V1). */
  reload(): void {
    window.location.reload();
  }
}
