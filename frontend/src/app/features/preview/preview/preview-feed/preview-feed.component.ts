// features/preview/preview/preview-feed/preview-feed.component.ts
// Selector: mee-preview-feed
// Feature-private child of PreviewComponent — Meesho-style feed card mock

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { InrCurrencyPipe } from '@shared/pipes/inr-currency.pipe';
import { PreviewData } from '../../preview-api.service';

@Component({
  selector: 'mee-preview-feed',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [InrCurrencyPipe],
  styles: [`
    :host { display: block; }
    .feed-card {
      width: 160px;
      border-radius: var(--mee-radius-md);
      background: var(--mee-color-surface);
      box-shadow: 0 1px 4px rgba(0,0,0,0.10);
      overflow: hidden;
    }
    .feed-thumb {
      width: 160px;
      height: 160px;
      object-fit: cover;
      display: block;
      background: #f0f5f9;
    }
    .feed-thumb-placeholder {
      width: 160px;
      height: 160px;
      background: var(--mee-color-bg);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--mee-color-outline);
      font-size: 40px;
    }
    .feed-body { padding: 8px; }
    .feed-title {
      font-size: 11px;
      color: var(--mee-color-on-surface);
      margin: 0 0 4px;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .feed-price {
      font-size: 13px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0;
    }
    .feed-category {
      font-size: 10px;
      color: #6B7280;
      margin: 4px 0 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .title-warning {
      display: inline-block;
      font-size: 9px;
      background: #FEF3C7;
      color: #92400E;
      border-radius: 4px;
      padding: 1px 4px;
      margin-left: 4px;
      vertical-align: middle;
    }
  `],
  template: `
    <div class="feed-card" role="article" aria-label="Feed card preview">
      <!-- Thumbnail: 1:1 square -->
      @if (thumbUrl()) {
        <img
          class="feed-thumb"
          [src]="thumbUrl()!"
          alt="Product image"
          loading="lazy"
        />
      } @else {
        <div class="feed-thumb-placeholder" aria-hidden="true">
          <span class="material-symbols-outlined" aria-hidden="true">image</span>
        </div>
      }

      <div class="feed-body">
        <!-- Title truncated at 30 chars with warning badge if > 30 chars -->
        <p class="feed-title">
          {{ truncatedTitle() }}
          @if (titleExceedsLimit()) {
            <span class="title-warning" title="Title exceeds 30 characters — may be cut off in feed">!</span>
          }
        </p>

        <!-- Price via inrCurrency pipe -->
        <p class="feed-price">{{ previewData().price | inrCurrency }}</p>

        <!-- Category path in muted text -->
        <p class="feed-category" [title]="previewData().category_path">
          {{ previewData().category_path }}
        </p>
      </div>
    </div>
  `,
})
export class PreviewFeedComponent {
  readonly previewData = input.required<PreviewData>();

  readonly thumbUrl = computed<string | null>(() => {
    const urls = this.previewData().image_urls;
    return urls && urls.length > 0 ? urls[0] : null;
  });

  readonly truncatedTitle = computed<string>(() => {
    const title = this.previewData().title;
    return title.length > 30 ? title.slice(0, 30) + '...' : title;
  });

  readonly titleExceedsLimit = computed<boolean>(() => {
    return this.previewData().title.length > 30;
  });
}
