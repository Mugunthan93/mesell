import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MeeToastComponent } from '@mesell/ui-kit';

@Component({
  selector: 'app-root',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, MeeToastComponent],
  template: `<router-outlet /><mee-toast />`,
})
export class AppComponent {}
