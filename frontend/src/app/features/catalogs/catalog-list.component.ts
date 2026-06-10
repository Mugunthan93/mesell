import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'mee-catalog-list',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="p-6"><h1 class="text-2xl font-semibold">My Catalogs</h1></div>`,
})
export class CatalogListComponent {}
