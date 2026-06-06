// shared/components/navbar/navbar.component.ts
// Stub — full implementation by meesell-angular-component-builder per §5.C.6
// Reads AuthService signals directly — documented exception to stateless rule in §5

import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';
import { AuthService } from '@core/auth/auth.service';

@Component({
  selector: 'mee-navbar',
  standalone: true,
  imports: [RouterModule, MatButtonModule, MatToolbarModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <mat-toolbar class="mee-navbar">
      <span><a routerLink="/">MeeSell</a></span>
      <span class="flex-1"></span>
      @if (auth.isAuthenticated()) {
        <button mat-button (click)="logout()">Logout</button>
      }
    </mat-toolbar>
  `,
})
export class NavbarComponent {
  protected readonly auth = inject(AuthService);

  logout(): void {
    this.auth.logout().subscribe();
  }
}
