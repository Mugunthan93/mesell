import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import {
  MeeButtonComponent,
  MeeCardComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import { PageHeaderComponent } from '@mesell/composites';

import {
  PreviewData,
  PreviewTab,
  MobileTile,
  SIMULATED_PREVIEW,
  FEED_TITLE_LIMIT,
  MOBILE_TITLE_LIMIT,
  DESKTOP_BREAKPOINT_PX,
  isTitleTruncated,
  truncateTitle,
  buildMobileTiles,
  resolveEditProductId,
} from './preview.model';

@Component({
  selector: 'app-preview',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MeeButtonComponent,
    MeeCardComponent,
    MeeSkeletonComponent,
    PageHeaderComponent,
  ],
  template: `
    <div class="flex flex-col gap-6 p-4 max-w-screen-xl mx-auto">

      <!-- Page header -->
      <mee-page-header
        title="Product Preview"
        subtitle="How your listing looks on Meesho"
      />

      <!-- Loading state: show card skeletons while data simulates -->
      @if (loading()) {
        <div class="flex flex-col gap-4 lg:flex-row">
          <div class="flex-1"><mee-skeleton variant="card" /></div>
          <div class="flex-1"><mee-skeleton variant="card" /></div>
          <div class="flex-1"><mee-skeleton variant="card" /></div>
        </div>
      } @else {

        <!-- Mobile-only tab chips: Feed / Detail / Mobile -->
        <div class="flex gap-2 lg:hidden" role="tablist" aria-label="Preview surfaces">
          @for (tab of tabs; track tab.key) {
            <button
              role="tab"
              [attr.aria-selected]="activeTab() === tab.key"
              class="min-h-[44px] px-4 rounded-full text-sm font-medium transition-colors"
              [style]="activeTab() === tab.key
                ? 'background:var(--mee-color-primary);color:var(--mee-color-on-primary);'
                : 'background:var(--mee-color-surface-variant);color:var(--mee-color-on-surface);'"
              (click)="onTabChange(tab.key)"
            >{{ tab.label }}</button>
          }
        </div>

        <!-- Preview surfaces: 3-column on desktop, single tab-controlled on mobile -->
        <div class="flex flex-col gap-6 lg:flex-row lg:gap-4">

          <!-- SURFACE 1 — Feed Thumbnail -->
          @if (isDesktop() || activeTab() === 'feed') {
            <div class="flex-1 flex flex-col gap-2" role="tabpanel" aria-label="Feed thumbnail">
              <mee-card>
                <div class="flex flex-col" style="background:var(--mee-color-surface);">

                  <!-- Product image 160×200 -->
                  <div
                    class="w-full overflow-hidden rounded-t"
                    style="height:200px;background:var(--mee-color-surface-variant);"
                  >
                    <img
                      [src]="preview()?.primary_image_url"
                      alt="Product image"
                      class="w-full h-full object-cover"
                      onerror="this.style.display='none'"
                    />
                  </div>

                  <div class="p-3 flex flex-col gap-1">
                    <!-- Truncation warning chip -->
                    @if (titleTruncated()) {
                      <span
                        class="text-xs font-semibold px-2 py-0.5 rounded self-start"
                        style="background:var(--mee-color-warning-light, rgba(234,179,8,0.15));color:var(--mee-color-warning, #ca8a04);"
                      >Title cuts at char {{ feedLimit }}</span>
                    }

                    <!-- Truncated title -->
                    <p
                      class="text-sm font-semibold leading-snug"
                      style="color:var(--mee-color-on-surface);"
                    >{{ truncatedFeedTitle() }}</p>

                    <!-- Price + rating row -->
                    <div class="flex items-center justify-between mt-1">
                      <span
                        class="text-base font-bold"
                        style="color:var(--mee-color-on-surface);"
                      >&#8377;{{ preview()?.mrp }}</span>
                      <span
                        class="text-xs"
                        style="color:var(--mee-color-on-surface-muted, #6b7280);"
                      >&#9733; 4.2 (120)</span>
                    </div>

                    <!-- Free delivery label -->
                    <p
                      class="text-xs"
                      style="color:var(--mee-color-success, #16a34a);"
                    >FREE delivery</p>
                  </div>

                </div>
              </mee-card>
              <p
                class="text-xs text-center font-medium"
                style="color:var(--mee-color-on-surface-muted, #6b7280);"
              >Feed thumbnail</p>
            </div>
          }

          <!-- SURFACE 2 — Detail Page -->
          @if (isDesktop() || activeTab() === 'detail') {
            <div class="flex-1 flex flex-col gap-2" role="tabpanel" aria-label="Detail page">
              <mee-card>
                <div class="flex flex-col" style="background:var(--mee-color-surface);">

                  <!-- Full-width product image -->
                  <div
                    class="w-full overflow-hidden rounded-t"
                    style="height:240px;background:var(--mee-color-surface-variant);"
                  >
                    <img
                      [src]="preview()?.primary_image_url"
                      alt="Product image"
                      class="w-full h-full object-cover"
                      onerror="this.style.display='none'"
                    />
                  </div>

                  <!-- Image dot indicators -->
                  <div class="flex justify-center gap-1.5 pt-2">
                    @for (url of preview()?.image_urls ?? []; track $index) {
                      <span
                        class="block rounded-full"
                        [style]="$index === 0
                          ? 'width:8px;height:8px;background:var(--mee-color-primary);'
                          : 'width:6px;height:6px;background:var(--mee-color-outline);'"
                        [attr.aria-label]="'Image ' + ($index + 1)"
                      ></span>
                    }
                  </div>

                  <div class="p-3 flex flex-col gap-2">
                    <!-- Full title -->
                    <h2
                      class="text-sm font-semibold leading-snug"
                      style="color:var(--mee-color-on-surface);"
                    >{{ preview()?.title }}</h2>

                    <!-- Price -->
                    <p
                      class="text-lg font-bold"
                      style="color:var(--mee-color-on-surface);"
                    >&#8377;{{ preview()?.mrp }}</p>

                    <!-- Commission + GST -->
                    <div class="flex gap-3 flex-wrap">
                      <span
                        class="text-xs"
                        style="color:var(--mee-color-on-surface-muted, #6b7280);"
                      >Commission: {{ preview()?.commission_pct }}%</span>
                      <span
                        class="text-xs"
                        style="color:var(--mee-color-on-surface-muted, #6b7280);"
                      >GST: {{ preview()?.gst_pct }}%</span>
                    </div>

                    <!-- Category path -->
                    <p
                      class="text-xs"
                      style="color:var(--mee-color-on-surface-muted, #6b7280);"
                    >{{ preview()?.category_path }}</p>

                    <!-- Simulated CTAs (non-interactive, visual only) -->
                    <div class="flex gap-2 mt-1">
                      <span
                        class="flex-1 text-center py-2 rounded text-sm font-semibold"
                        style="border:1px solid var(--mee-color-primary);color:var(--mee-color-primary);"
                        aria-hidden="true"
                      >Add to cart</span>
                      <span
                        class="flex-1 text-center py-2 rounded text-sm font-semibold"
                        style="background:var(--mee-color-primary);color:var(--mee-color-on-primary);"
                        aria-hidden="true"
                      >Buy now</span>
                    </div>
                  </div>

                </div>
              </mee-card>
              <p
                class="text-xs text-center font-medium"
                style="color:var(--mee-color-on-surface-muted, #6b7280);"
              >Detail page</p>
            </div>
          }

          <!-- SURFACE 3 — Mobile Grid Card (2-up style) -->
          @if (isDesktop() || activeTab() === 'mobile') {
            <div class="flex-1 flex flex-col gap-2" role="tabpanel" aria-label="Mobile grid card">
              <mee-card>
                <div
                  class="p-2"
                  style="background:var(--mee-color-surface);"
                >
                  <!-- 2-up mobile grid: two tiles side-by-side -->
                  <div class="grid grid-cols-2 gap-2">
                    @for (tile of mobileTiles(); track $index) {
                      <div
                        class="flex flex-col gap-1"
                        style="background:var(--mee-color-surface-variant);border-radius:var(--mee-radius-sm, 4px);overflow:hidden;"
                      >
                        <!-- Tile image -->
                        <div style="height:100px;background:var(--mee-color-outline);">
                          <img
                            [src]="tile.imageUrl"
                            alt="Product tile"
                            class="w-full h-full object-cover"
                            onerror="this.style.display='none'"
                          />
                        </div>

                        <!-- Truncated title + price -->
                        <div class="p-1 flex flex-col gap-0.5">
                          <p
                            class="text-xs font-medium leading-tight"
                            style="color:var(--mee-color-on-surface);"
                          >{{ tile.truncatedTitle }}</p>
                          <p
                            class="text-xs font-bold"
                            style="color:var(--mee-color-on-surface);"
                          >&#8377;{{ preview()?.mrp }}</p>
                        </div>
                      </div>
                    }
                  </div>
                </div>
              </mee-card>
              <p
                class="text-xs text-center font-medium"
                style="color:var(--mee-color-on-surface-muted, #6b7280);"
              >Mobile grid card</p>
            </div>
          }

        </div>

        <!-- Title truncation warning panel -->
        @if (titleTruncated()) {
          <div
            class="rounded-lg p-4 flex gap-3 items-start"
            style="background:var(--mee-color-warning-light, rgba(234,179,8,0.1));border:1px solid var(--mee-color-warning, #ca8a04);"
            role="alert"
            aria-live="polite"
          >
            <span
              class="text-lg leading-none"
              aria-hidden="true"
              style="color:var(--mee-color-warning, #ca8a04);"
            >&#9888;</span>
            <div class="flex flex-col gap-1">
              <p
                class="text-sm font-semibold"
                style="color:var(--mee-color-warning, #ca8a04);"
              >Title truncation warning</p>
              <p
                class="text-sm"
                style="color:var(--mee-color-on-surface);"
              >
                &ldquo;{{ truncatedFeedTitle() }}&rdquo;
                &mdash; title cut at char {{ feedLimit }} on mobile feed view.
              </p>
              <p
                class="text-xs mt-1"
                style="color:var(--mee-color-on-surface-muted, #6b7280);"
              >
                Your title is {{ preview()?.title?.length ?? 0 }} chars.
                Aim for &#8804;{{ feedLimit }} chars for the best feed appearance.
              </p>
            </div>
          </div>
        }

        <!-- Edit product CTA -->
        <div class="flex justify-start">
          <mee-button
            label="Edit product"
            variant="secondary"
            (clicked)="onEditProduct()"
          />
        </div>

      }
    </div>
  `,
})
export class PreviewComponent implements OnInit {
  private readonly route  = inject(ActivatedRoute);
  private readonly router = inject(Router);

  // Component state
  readonly loading   = signal<boolean>(true);
  readonly preview   = signal<PreviewData | null>(null);
  readonly activeTab = signal<PreviewTab>('feed');
  readonly isDesktop = signal<boolean>(
    typeof window !== 'undefined' ? window.innerWidth >= DESKTOP_BREAKPOINT_PX : true
  );

  // Public constants exposed to template
  readonly feedLimit   = FEED_TITLE_LIMIT;
  readonly mobileLimit = MOBILE_TITLE_LIMIT;

  // Derived display values — delegate to pure model functions
  readonly titleTruncated = computed<boolean>(
    () => isTitleTruncated(this.preview()?.title)
  );

  readonly truncatedFeedTitle = computed<string>(
    () => truncateTitle(this.preview()?.title, FEED_TITLE_LIMIT)
  );

  readonly mobileTiles = computed<MobileTile[]>(
    () => buildMobileTiles(this.preview())
  );

  // Tab definitions — used in the mobile chip row
  readonly tabs: Array<{ key: PreviewTab; label: string }> = [
    { key: 'feed',   label: 'Feed' },
    { key: 'detail', label: 'Detail' },
    { key: 'mobile', label: 'Mobile' },
  ];

  ngOnInit(): void {
    // Simulate 800ms network delay before presenting preview data
    setTimeout(() => {
      this.preview.set(SIMULATED_PREVIEW);
      this.loading.set(false);
    }, 800);
  }

  onTabChange(tab: PreviewTab): void {
    this.activeTab.set(tab);
  }

  onEditProduct(): void {
    const productId = resolveEditProductId(
      this.route.snapshot.paramMap.get('id'),
      this.preview()?.product_id
    );
    this.router.navigate(['/catalogs', productId, 'edit']);
  }
}
