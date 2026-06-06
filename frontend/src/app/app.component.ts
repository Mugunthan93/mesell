// app.component.ts — Root standalone component.
// AMENDMENT 2026-06-06 (Phase 2 app shell): Simplified to bare router-outlet.
// NavbarComponent removed — navigation is now handled by MeeShellComponent (authenticated routes)
// and MeeAuthLayoutComponent (unauthenticated routes). OfflineBannerComponent retained
// at root so it always appears regardless of layout context.
// SW update notification retained.

import { ChangeDetectionStrategy, Component, inject, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { filter } from 'rxjs/operators';
import { SwUpdate } from '@angular/service-worker';
import { MatSnackBar } from '@angular/material/snack-bar';
import { OfflineBannerComponent } from '@shared/components/offline-banner/offline-banner.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, OfflineBannerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<mee-offline-banner /><router-outlet />`,
  styleUrl: './app.component.scss',
})
export class AppComponent implements OnInit {
  private readonly swUpdate = inject(SwUpdate, { optional: true });
  private readonly snackBar = inject(MatSnackBar);

  ngOnInit(): void {
    // Service worker update notification per §20.H
    if (this.swUpdate?.isEnabled) {
      this.swUpdate.versionUpdates.pipe(
        filter(e => e.type === 'VERSION_READY'),
      ).subscribe(() => {
        this.snackBar.open('A new version is available', 'Reload', { duration: 0 })
          .onAction()
          .subscribe(() => location.reload());
      });
    }
  }
}
