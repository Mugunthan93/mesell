import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Output,
} from '@angular/core';
import { MatChipsModule, MatChipListboxChange } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoPipe } from '@jsverse/transloco';

interface SuperCategory {
  readonly id: string;
  readonly labelKey: string;
  readonly icon: string;
}

@Component({
  selector: 'mee-super-category-chips',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatChipsModule, MatIconModule, TranslocoPipe],
  template: `
    <div class="space-y-3">
      <p class="text-mee-sm text-on-surface-variant">
        {{ 'onboarding.chips.help' | transloco }}
      </p>
      <mat-chip-listbox
        multiple
        [attr.aria-label]="'onboarding.chips.ariaLabel' | transloco"
        (change)="onSelectionChange($event)"
        class="flex flex-wrap gap-2">
        @for (cat of SUPER_CATEGORIES; track cat.id) {
          <mat-chip-option
            [value]="cat.id"
            color="primary"
            class="bg-light-primary">
            <mat-icon matChipAvatar class="text-mee-base">{{ cat.icon }}</mat-icon>
            {{ cat.labelKey | transloco }}
          </mat-chip-option>
        }
      </mat-chip-listbox>
    </div>
  `,
})
export class SuperCategoryChipsComponent {
  // Static data — hardcoded constant matching COMPLIANCE_EXTENSION_MAP exactly.
  // NOTE: Beauty chip emits super_id '19' (primary). Full Beauty super_id expansion
  // (19/36/37/14/88/34) is handled in the API service (Dispatch 4), not here.
  readonly SUPER_CATEGORIES: ReadonlyArray<SuperCategory> = [
    { id: '26', labelKey: 'onboarding.chips.grocery',     icon: 'storefront'  },
    { id: '13', labelKey: 'onboarding.chips.kids',        icon: 'child_care'  },
    { id: '16', labelKey: 'onboarding.chips.electronics', icon: 'devices'     },
    { id: '19', labelKey: 'onboarding.chips.beauty',      icon: 'spa'         },
    { id: '80', labelKey: 'onboarding.chips.books',       icon: 'menu_book'   },
    { id: '30', labelKey: 'onboarding.chips.appliances',  icon: 'kitchen'     },
  ];

  @Output() readonly selectionChange = new EventEmitter<string[]>();

  onSelectionChange(event: MatChipListboxChange): void {
    // MatChipListboxChange.value is the array of currently selected chip values.
    // Null-coalesce to [] when the listbox has no selection (all chips deselected).
    this.selectionChange.emit((event.value as string[]) ?? []);
  }
}
