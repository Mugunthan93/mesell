// features/preview/preview/preview-detail/preview-detail.component.ts
// Selector: mee-preview-detail
// Feature-private child of PreviewComponent — Meesho product detail page mock

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { InrCurrencyPipe } from '@shared/pipes/inr-currency.pipe';
import { PreviewData } from '../../preview-api.service';

@Component({
  selector: 'mee-preview-detail',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [InrCurrencyPipe],
  styles: [`
    :host { display: block; }
    .detail-mock {
      background: var(--mee-color-surface);
      border-radius: var(--mee-radius-md);
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,0.10);
      max-width: 480px;
    }
    .detail-hero {
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: cover;
      display: block;
      background: var(--mee-color-bg);
    }
    .detail-hero-placeholder {
      width: 100%;
      aspect-ratio: 1 / 1;
      background: var(--mee-color-bg);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--mee-color-outline);
      font-size: 72px;
    }
    .detail-body { padding: 16px; }
    .detail-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin: 0 0 8px;
      line-height: 1.5;
    }
    .detail-price {
      font-size: 20px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0 0 10px;
    }
    .detail-variant {
      font-size: 13px;
      color: #374151;
      background: var(--mee-color-bg);
      border-radius: 6px;
      padding: 6px 10px;
      margin: 0 0 10px;
      display: inline-block;
    }
    .detail-desc {
      font-size: 13px;
      color: #6B7280;
      line-height: 1.6;
      margin: 0 0 10px;
    }
    .detail-readmore {
      font-size: 12px;
      color: var(--mee-color-primary);
      cursor: pointer;
    }
    .detail-breadcrumb {
      font-size: 11px;
      color: #9CA3AF;
      margin: 0;
      padding-top: 10px;
      border-top: 1px solid var(--mee-color-bg);
    }
  `],
  template: `
    <div class="detail-mock" role="article" aria-label="Product detail preview">
      <!-- Hero image — full width, 1:1 aspect ratio -->
      @if (heroUrl()) {
        <img
          class="detail-hero"
          [src]="heroUrl()!"
          alt="Product main image"
          loading="lazy"
        />
      } @else {
        <div class="detail-hero-placeholder" aria-hidden="true">
          <span class="material-symbols-outlined" aria-hidden="true">image</span>
        </div>
      }

      <div class="detail-body">
        <!-- Full title — no truncation -->
        <p class="detail-title">{{ previewData().title }}</p>

        <!-- Price with ₹ prefix via inrCurrency pipe -->
        <p class="detail-price">{{ previewData().price | inrCurrency }}</p>

        <!-- First variant if non-null -->
        @if (previewData().first_variant) {
          <span class="detail-variant" aria-label="Variant">{{ previewData().first_variant }}</span>
        }

        <!-- Description (first 200 chars + "Read more" if longer) -->
        @if (previewData().full_description) {
          <p class="detail-desc">
            {{ shortDescription() }}
            @if (descriptionTruncated()) {
              <span class="detail-readmore" role="button" tabindex="0" aria-label="Read more description">Read more</span>
            }
          </p>
        }

        <!-- Category breadcrumb -->
        <p class="detail-breadcrumb" aria-label="Category">
          {{ previewData().category_path }}
        </p>
      </div>
    </div>
  `,
})
export class PreviewDetailComponent {
  readonly previewData = input.required<PreviewData>();

  readonly heroUrl = computed<string | null>(() => {
    const urls = this.previewData().image_urls;
    return urls && urls.length > 0 ? urls[0] : null;
  });

  readonly shortDescription = computed<string>(() => {
    const desc = this.previewData().full_description;
    if (!desc) return '';
    return desc.length > 200 ? desc.slice(0, 200) + '...' : desc;
  });

  readonly descriptionTruncated = computed<boolean>(() => {
    const desc = this.previewData().full_description;
    return !!desc && desc.length > 200;
  });
}
