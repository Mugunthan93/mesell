import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  signal,
} from '@angular/core';

import {
  MeeBadgeComponent,
  MeeButtonComponent,
  MeeCardComponent,
  MeeFileUploadComponent,
  MeeIconComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import type { MeeFileUploadEvent } from '@mesell/ui-kit';
import {
  EmptyStateComponent,
  MeeAlertBannerComponent,
  PageHeaderComponent,
} from '@mesell/composites';
import { MeePageComponent } from '@mesell/layout';

import {
  InvalidInventoryFileError,
  LiveListing,
  LOCAL_STORAGE_KEY,
  INVENTORY_SHEET_NAME,
  ParsedInventory,
  mapSheetToInventory,
} from './live-listings.model';

// ─── Component state ───────────────────────────────────────────────────────────

type PageState = 'idle' | 'parsing' | 'parsed' | 'invalid-file' | 'all-skipped';

// ─── Component ────────────────────────────────────────────────────────────────

@Component({
  selector: 'app-live-listings',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    // @mesell/ui-kit
    MeeBadgeComponent,
    MeeButtonComponent,
    MeeCardComponent,
    MeeFileUploadComponent,
    MeeIconComponent,
    MeeSkeletonComponent,
    // @mesell/composites
    EmptyStateComponent,
    MeeAlertBannerComponent,
    PageHeaderComponent,
    MeePageComponent,
  ],
  template: `
    <mee-page maxWidth="xl">

      <!-- Page header -->
      <mee-page-header
        title="My Live Listings"
        subtitle="Upload your Meesho Inventory Update File to get direct links to your live products."
      />

      <!-- ── IDLE / EMPTY STATE ──────────────────────────────────────────────── -->
      @if (pageState() === 'idle') {
        <mee-empty-state
          icon="link"
          message="No listings loaded yet. Upload your Inventory Update File to see your live products."
        />

        <!-- Upload card -->
        <mee-card>
          <div class="flex flex-col gap-4 p-2">
            <mee-file-upload
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              [max_size_mb]="25"
              [multiple]="false"
              label="Select Inventory Update File (.xlsx)"
              (files_selected)="onFilesSelected($event)"
              (upload_error)="onFileError($event)"
            />
            <p class="text-sm" style="color: var(--mee-color-on-surface-muted);">
              Download your Inventory Update File from your Meesho supplier panel,
              then upload it here.
            </p>
          </div>
        </mee-card>
      }

      <!-- ── PARSING / LOADING ───────────────────────────────────────────────── -->
      @if (pageState() === 'parsing') {
        <div class="flex flex-col gap-4">
          <mee-skeleton variant="table-row" />
          <mee-skeleton variant="table-row" />
          <mee-skeleton variant="table-row" />
          <mee-skeleton variant="table-row" />
          <mee-skeleton variant="table-row" />
        </div>
      }

      <!-- ── INVALID FILE ERROR ────────────────────────────────────────────────── -->
      @if (pageState() === 'invalid-file') {
        <mee-alert-banner
          variant="error"
          message="This doesn't look like a Meesho Inventory Update File. Download it from your Meesho supplier panel and upload that .xlsx."
        />
        <mee-card>
          <div class="flex flex-col gap-4 p-2">
            <mee-file-upload
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              [max_size_mb]="25"
              [multiple]="false"
              label="Select Inventory Update File (.xlsx)"
              (files_selected)="onFilesSelected($event)"
              (upload_error)="onFileError($event)"
            />
          </div>
        </mee-card>
      }

      <!-- ── ALL-SKIPPED INFO ─────────────────────────────────────────────────── -->
      @if (pageState() === 'all-skipped') {
        <mee-alert-banner
          variant="warning"
          [message]="allSkippedMessage()"
        />
        <mee-card>
          <div class="flex flex-col gap-4 p-2">
            <mee-file-upload
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              [max_size_mb]="25"
              [multiple]="false"
              label="Select a different file"
              (files_selected)="onFilesSelected($event)"
              (upload_error)="onFileError($event)"
            />
          </div>
        </mee-card>
      }

      <!-- ── PARSED TABLE / CARDS ─────────────────────────────────────────────── -->
      @if (pageState() === 'parsed') {

        <!-- Summary row + clear action -->
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm font-medium" style="color: var(--mee-color-on-surface);">
            {{ summaryText() }}
          </p>
          <mee-button
            label="Upload a different file / Clear"
            variant="secondary"
            (clicked)="onClear()"
          />
        </div>

        <!-- DESKTOP TABLE (>=768px) — uses mee-card + native table for a11y -->
        <div class="hidden md:block">
          <mee-card>
            <div style="overflow-x: auto;">
              <table class="w-full text-sm" style="border-collapse: collapse;">
                <thead>
                  <tr style="border-bottom: 1px solid var(--mee-color-outline);">
                    <th
                      class="text-left px-4 py-3 font-semibold"
                      style="color: var(--mee-color-on-surface); min-width: 280px;"
                      scope="col"
                    >Product</th>
                    <th
                      class="text-left px-4 py-3 font-semibold"
                      style="color: var(--mee-color-on-surface); min-width: 120px;"
                      scope="col"
                    >Product ID</th>
                    <th
                      class="text-left px-4 py-3 font-semibold"
                      style="color: var(--mee-color-on-surface); min-width: 160px;"
                      scope="col"
                    >View on Meesho</th>
                  </tr>
                </thead>
                <tbody>
                  @for (listing of listings(); track listing.productId) {
                    <tr
                      style="border-bottom: 1px solid var(--mee-color-outline);"
                      class="hover:opacity-80 transition-opacity"
                    >
                      <td class="px-4 py-3" style="color: var(--mee-color-on-surface);">
                        {{ listing.productName || '(No name)' }}
                      </td>
                      <td class="px-4 py-3">
                        <mee-badge [value]="listing.productId" severity="neutral" />
                      </td>
                      <td class="px-4 py-3">
                        <a
                          [href]="listing.meeshoUrl"
                          target="_blank"
                          rel="noopener noreferrer"
                          [attr.aria-label]="'View ' + (listing.productName || 'product') + ' on Meesho (opens in a new tab)'"
                          class="inline-flex items-center gap-1 min-h-[44px] font-medium underline"
                          style="color: var(--mee-color-primary);"
                        >
                          <span>View on Meesho</span>
                          <mee-icon name="external-link" />
                        </a>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </mee-card>
        </div>

        <!-- MOBILE CARDS (<768px) -->
        <div class="flex flex-col gap-3 md:hidden">
          @for (listing of listings(); track listing.productId) {
            <mee-card>
              <div class="flex flex-col gap-3 p-1">
                <!-- Product name -->
                <p class="text-sm font-semibold" style="color: var(--mee-color-on-surface);">
                  {{ listing.productName || '(No name)' }}
                </p>

                <!-- Product ID badge -->
                <div class="flex items-center gap-2">
                  <span class="text-xs" style="color: var(--mee-color-on-surface-muted);">ID:</span>
                  <mee-badge [value]="listing.productId" severity="neutral" />
                </div>

                <!-- Full-width View on Meesho link -->
                <a
                  [href]="listing.meeshoUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  [attr.aria-label]="'View ' + (listing.productName || 'product') + ' on Meesho (opens in a new tab)'"
                  class="flex items-center justify-center gap-2 w-full min-h-[44px] rounded font-semibold text-sm"
                  style="background: var(--mee-color-primary); color: var(--mee-color-on-primary); text-decoration: none;"
                >
                  <span>View on Meesho</span>
                  <mee-icon name="external-link" />
                </a>
              </div>
            </mee-card>
          }
        </div>

      }

    </mee-page>
  `,
})
export class LiveListingsComponent implements OnInit {

  // ── Signals ─────────────────────────────────────────────────────────────────

  readonly pageState   = signal<PageState>('idle');
  readonly listings    = signal<LiveListing[]>([]);
  readonly skippedCount = signal<number>(0);

  // ── Computed ─────────────────────────────────────────────────────────────────

  readonly summaryText = computed(() => {
    const count = this.listings().length;
    const skipped = this.skippedCount();
    const parts = [`${count} listing${count !== 1 ? 's' : ''}`];
    if (skipped > 0) parts.push(`${skipped} skipped`);
    return parts.join(' · ');
  });

  readonly allSkippedMessage = computed(() => {
    const skipped = this.skippedCount();
    return `All ${skipped} row${skipped !== 1 ? 's' : ''} were skipped — no valid numeric Product IDs found. ` +
           `Please check that you uploaded the correct Meesho Inventory Update File.`;
  });

  // ── Lifecycle ────────────────────────────────────────────────────────────────

  ngOnInit(): void {
    this.hydrateFromLocalStorage();
  }

  // ── Event handlers ────────────────────────────────────────────────────────────

  async onFilesSelected(event: MeeFileUploadEvent): Promise<void> {
    const file = event.files[0];
    if (!file) return;

    this.pageState.set('parsing');

    try {
      const arrayBuffer = await file.arrayBuffer();

      // Lazy-import xlsx — MUST remain async so it lands in a separate chunk
      const XLSX = await import('xlsx');

      const workbook = XLSX.read(arrayBuffer, { type: 'array' });

      // Pick the inventory sheet by name; fall back to first sheet if not found
      const sheetName =
        workbook.SheetNames.includes(INVENTORY_SHEET_NAME)
          ? INVENTORY_SHEET_NAME
          : workbook.SheetNames[0];

      const worksheet = workbook.Sheets[sheetName];

      const rawRows = XLSX.utils.sheet_to_json<unknown[]>(worksheet, {
        header: 1,
        blankrows: false,
      });

      const parsed: ParsedInventory = mapSheetToInventory(rawRows as unknown[][]);

      this.listings.set(parsed.listings);
      this.skippedCount.set(parsed.skippedCount);

      if (parsed.listings.length === 0) {
        this.pageState.set('all-skipped');
        this.persistToLocalStorage(parsed);
      } else {
        this.pageState.set('parsed');
        this.persistToLocalStorage(parsed);
      }
    } catch (err) {
      if (err instanceof InvalidInventoryFileError) {
        this.pageState.set('invalid-file');
      } else {
        // Unknown parse error — treat as invalid file
        this.pageState.set('invalid-file');
      }
    }
  }

  onFileError(_errorMessage: string): void {
    this.pageState.set('invalid-file');
  }

  onClear(): void {
    this.listings.set([]);
    this.skippedCount.set(0);
    this.pageState.set('idle');
    try {
      localStorage.removeItem(LOCAL_STORAGE_KEY);
    } catch {
      // localStorage may be unavailable (e.g., private mode restrictions)
    }
  }

  // ── Storage helpers ────────────────────────────────────────────────────────────

  private persistToLocalStorage(parsed: ParsedInventory): void {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(parsed));
    } catch {
      // Storage quota or access error — silently skip persistence
    }
  }

  private hydrateFromLocalStorage(): void {
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (!raw) return;

      const parsed = JSON.parse(raw) as ParsedInventory;
      if (!Array.isArray(parsed?.listings)) return;

      this.listings.set(parsed.listings);
      this.skippedCount.set(parsed.skippedCount ?? 0);

      if (parsed.listings.length === 0) {
        this.pageState.set('all-skipped');
      } else {
        this.pageState.set('parsed');
      }
    } catch {
      // Corrupted storage — silently ignore
    }
  }
}
