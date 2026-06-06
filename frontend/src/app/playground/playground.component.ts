/**
 * Theme Playground
 * One dropdown → iframe renders the selected theme's full build.
 * Add more themes by dropping their built output in src/assets/themes/{id}/
 * and adding an entry to THEME_CATALOG below.
 */
import {
  Component,
  signal,
  computed,
  inject,
  ChangeDetectionStrategy,
  ElementRef,
  viewChild,
  effect,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

export interface ThemeCatalogEntry {
  id: string;
  name: string;
  description: string;
  stack: string;
  tags: string[];
  assetPath: string;   // relative to /assets/themes/
  previewRoute: string; // hash/path inside the built app
  screenshots?: string[];
}

const THEME_CATALOG: ThemeCatalogEntry[] = [
  {
    id: 'spike',
    name: 'Spike Angular',
    description: 'Material Design admin — Angular 21 + Angular Material. Clean sidebar, data tables, form controls.',
    stack: 'Angular 21 + Angular Material',
    tags: ['Material', 'Sidebar', 'Tables', 'Forms'],
    assetPath: 'spike',
    previewRoute: '',
  },
];

@Component({
  selector: 'app-playground',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display:flex; flex-direction:column; height:100%; min-height:0; background:#f8fafc; overflow:hidden; }

    /* ── Top bar ─────────────────────────────────────────────────────── */
    .topbar {
      display:flex; align-items:center; gap:16px;
      padding:12px 20px;
      background:#fff;
      border-bottom:1px solid #e4e7ec;
      flex-shrink:0;
    }
    .topbar-brand {
      font-size:13px; font-weight:700; color:#111827; letter-spacing:-.2px;
      white-space:nowrap;
    }
    .topbar-brand span { color:#f36f21; }
    .topbar-divider { width:1px; height:20px; background:#e4e7ec; }

    /* Theme selector */
    .theme-selector {
      display:flex; align-items:center; gap:10px; flex:1;
    }
    .theme-label {
      font-size:12px; font-weight:600; color:#6b7280;
      text-transform:uppercase; letter-spacing:.5px; white-space:nowrap;
    }
    .theme-select {
      height:36px; padding:0 32px 0 12px;
      border:1px solid #d1d5db; border-radius:8px;
      font-size:13px; font-weight:500; color:#111827;
      background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E") no-repeat right 10px center;
      -webkit-appearance:none; appearance:none; cursor:pointer; outline:none;
      min-width:240px;
    }
    .theme-select:focus { border-color:#f36f21; box-shadow:0 0 0 3px rgba(243,111,33,.12); }

    /* Meta pill */
    .theme-meta { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
    .meta-tag {
      padding:3px 8px; border-radius:9999px;
      font-size:11px; font-weight:500;
      background:#f1f5f9; color:#475569;
    }
    .meta-stack {
      font-size:11px; color:#9ca3af; white-space:nowrap;
    }

    /* Action buttons */
    .topbar-actions { display:flex; align-items:center; gap:8px; margin-left:auto; }
    .btn-ghost {
      height:32px; padding:0 12px; border-radius:7px;
      border:1px solid #e4e7ec; background:#fff;
      font-size:12px; font-weight:500; color:#374151;
      cursor:pointer; display:flex; align-items:center; gap:6px;
      transition:border-color .15s, background .15s;
    }
    .btn-ghost:hover { border-color:#d1d5db; background:#f9fafb; }
    .btn-ghost svg { width:14px; height:14px; stroke:#6b7280; }

    /* ── Route bar ───────────────────────────────────────────────────── */
    .routebar {
      display:flex; align-items:center; gap:0;
      padding:8px 20px 0;
      background:#fff;
      border-bottom:1px solid #e4e7ec;
      flex-shrink:0; overflow-x:auto;
    }
    .route-btn {
      padding:8px 14px; font-size:12px; font-weight:500; color:#6b7280;
      border:none; background:transparent; cursor:pointer; white-space:nowrap;
      border-bottom:2px solid transparent; margin-bottom:-1px;
      transition:color .15s, border-color .15s;
    }
    .route-btn:hover { color:#374151; }
    .route-btn.active { color:#f36f21; border-bottom-color:#f36f21; font-weight:600; }

    /* ── Viewport shell ──────────────────────────────────────────────── */
    .viewport-shell {
      flex:1; min-height:0; display:flex; flex-direction:column; overflow:hidden;
      position:relative;
    }

    /* Device toolbar */
    .device-toolbar {
      display:flex; align-items:center; justify-content:center; gap:6px;
      padding:6px 20px;
      background:#f8fafc; border-bottom:1px solid #e4e7ec;
      flex-shrink:0;
    }
    .device-btn {
      height:28px; padding:0 10px; border-radius:6px;
      border:1px solid transparent; background:transparent;
      font-size:11px; font-weight:500; color:#6b7280;
      cursor:pointer; display:flex; align-items:center; gap:4px;
      transition:all .15s;
    }
    .device-btn:hover { background:#fff; border-color:#e4e7ec; color:#374151; }
    .device-btn.active { background:#fff; border-color:#d1d5db; color:#111827; font-weight:600; }
    .device-btn svg { width:13px; height:13px; stroke:currentColor; }
    .device-divider { width:1px; height:16px; background:#e4e7ec; }
    .device-size-label { font-size:11px; color:#9ca3af; min-width:80px; text-align:center; }

    /* iframe wrapper */
    .iframe-wrapper {
      flex:1; display:flex; justify-content:center; overflow:auto;
      padding:0; background:#e5e7eb;
      transition:padding .2s;
    }
    .iframe-wrapper.device-mobile { padding:16px; }
    .iframe-wrapper.device-tablet { padding:12px; }

    .iframe-frame {
      width:100%; height:100%; border:none;
      background:#fff;
      transition:width .25s ease, height .25s ease, box-shadow .25s;
    }
    .iframe-frame.device-mobile {
      width:390px; max-height:844px;
      border-radius:24px;
      box-shadow:0 0 0 2px #374151, 0 20px 60px rgba(0,0,0,.25);
    }
    .iframe-frame.device-tablet {
      width:768px; max-height:1024px;
      border-radius:16px;
      box-shadow:0 0 0 2px #374151, 0 12px 40px rgba(0,0,0,.18);
    }

    /* ── Loading overlay ─────────────────────────────────────────────── */
    .loading-overlay {
      position:absolute; inset:0; z-index:10;
      display:flex; flex-direction:column; align-items:center; justify-content:center;
      background:#f8fafc; gap:14px;
      pointer-events:none;
    }
    .loading-spinner {
      width:36px; height:36px; border-radius:50%;
      border:3px solid #e4e7ec; border-top-color:#f36f21;
      animation:spin .7s linear infinite;
    }
    @keyframes spin { to { transform:rotate(360deg); } }
    .loading-text { font-size:13px; color:#6b7280; font-weight:500; }

    /* ── Empty state ─────────────────────────────────────────────────── */
    .empty-state {
      flex:1; display:flex; flex-direction:column;
      align-items:center; justify-content:center; gap:12px;
      color:#9ca3af;
    }
    .empty-state-icon { font-size:40px; }
    .empty-state h3 { font-size:16px; font-weight:600; color:#374151; margin:0; }
    .empty-state p  { font-size:13px; margin:0; text-align:center; max-width:300px; line-height:1.6; }
  `],
  template: `
    <!-- ── Top bar ────────────────────────────────────────────────────── -->
    <div class="topbar">
      <div class="topbar-brand">Mee<span>Sell</span> Themes</div>
      <div class="topbar-divider"></div>

      <!-- Dropdown -->
      <div class="theme-selector">
        <span class="theme-label">Theme</span>
        <select
          class="theme-select"
          (change)="onThemeChange($event)"
        >
          <option value="" [selected]="selectedId() === ''">— Select a theme —</option>
          @for (t of themes; track t.id) {
            <option [value]="t.id" [selected]="selectedId() === t.id">{{ t.name }}</option>
          }
        </select>
      </div>

      <!-- Meta pills for selected theme -->
      @if (selectedTheme()) {
        <div class="theme-meta">
          @for (tag of selectedTheme()!.tags; track tag) {
            <span class="meta-tag">{{ tag }}</span>
          }
          <span class="meta-stack">{{ selectedTheme()!.stack }}</span>
        </div>
      }

      <!-- Actions -->
      <div class="topbar-actions">
        <button class="btn-ghost" (click)="reloadIframe()" title="Reload">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
            <path d="M1 4v6h6M23 20v-6h-6"/>
            <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"/>
          </svg>
          Reload
        </button>
        @if (selectedTheme()) {
          <button class="btn-ghost" (click)="openExternal()" title="Open in new tab">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            Open
          </button>
        }
      </div>
    </div>

    <!-- ── Route bar (quick nav inside the theme) ────────────────────── -->
    @if (selectedTheme()) {
      <div class="routebar">
        @for (r of currentRoutes(); track r.path) {
          <button
            class="route-btn"
            [class.active]="activeRoute() === r.path"
            (click)="navigateTo(r.path)"
          >{{ r.label }}</button>
        }
      </div>
    }

    <!-- ── Viewport ───────────────────────────────────────────────────── -->
    <div class="viewport-shell">

      <!-- Device toolbar -->
      @if (selectedTheme()) {
        <div class="device-toolbar">
          <button class="device-btn" [class.active]="device() === 'desktop'" (click)="device.set('desktop')">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
            </svg>
            Desktop
          </button>
          <button class="device-btn" [class.active]="device() === 'tablet'" (click)="device.set('tablet')">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
              <rect x="4" y="2" width="16" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>
            </svg>
            Tablet
          </button>
          <button class="device-btn" [class.active]="device() === 'mobile'" (click)="device.set('mobile')">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
              <rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>
            </svg>
            Mobile
          </button>
          <div class="device-divider"></div>
          <span class="device-size-label">{{ deviceLabel() }}</span>
        </div>
      }

      <!-- iframe -->
      @if (selectedTheme()) {
        <div class="iframe-wrapper" [class]="'device-' + device()">
          @if (loading()) {
            <div class="loading-overlay">
              <div class="loading-spinner"></div>
              <span class="loading-text">Loading {{ selectedTheme()!.name }}…</span>
            </div>
          }
          <iframe
            #themeFrame
            class="iframe-frame"
            [class]="'device-' + device()"
            [src]="iframeSrc()"
            (load)="onIframeLoad()"
            sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
            loading="lazy"
          ></iframe>
        </div>
      } @else {
        <div class="empty-state">
          <div class="empty-state-icon">🎨</div>
          <h3>Pick a theme to preview</h3>
          <p>Select a theme from the dropdown above to see how it looks for MeeSell.</p>
        </div>
      }
    </div>
  `,
})
export class PlaygroundComponent {
  private sanitizer = inject(DomSanitizer);

  readonly themes = THEME_CATALOG;

  selectedId = signal<string>('spike');  // default: Spike
  device     = signal<'desktop' | 'tablet' | 'mobile'>('desktop');
  loading    = signal(true);
  activeRoute = signal('');

  themeFrame = viewChild<ElementRef<HTMLIFrameElement>>('themeFrame');

  selectedTheme = computed(() =>
    this.themes.find(t => t.id === this.selectedId()) ?? null
  );

  iframeSrc = computed((): SafeResourceUrl => {
    const theme = this.selectedTheme();
    if (!theme) return this.sanitizer.bypassSecurityTrustResourceUrl('about:blank');
    const route = this.activeRoute();
    const base = `/themes/${theme.assetPath}/index.html`;
    const url = route ? `${base}#/${route}` : base;
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  });

  deviceLabel = computed(() => {
    const d = this.device();
    if (d === 'mobile')  return '390 × 844';
    if (d === 'tablet')  return '768 × 1024';
    return 'Full width';
  });

  // Route quick-nav per theme (extend as more themes added)
  currentRoutes = computed(() => {
    const id = this.selectedId();
    if (id === 'spike') {
      return [
        { path: '',                label: 'Dashboard' },
        { path: 'ui-components/tables',  label: 'Tables' },
        { path: 'ui-components/forms',   label: 'Forms' },
        { path: 'ui-components/badge',   label: 'Badges' },
        { path: 'ui-components/chips',   label: 'Chips' },
        { path: 'ui-components/lists',   label: 'Lists' },
        { path: 'ui-components/menu',    label: 'Menu' },
        { path: 'extra/icons',           label: 'Icons' },
        { path: 'authentication/login',  label: 'Login' },
      ];
    }
    return [{ path: '', label: 'Home' }];
  });

  constructor() {
    // Reset loading + route when theme changes
    effect(() => {
      this.selectedId();
      this.loading.set(true);
      this.activeRoute.set('');
    });
  }

  onThemeChange(e: Event) {
    const val = (e.target as HTMLSelectElement).value;
    this.selectedId.set(val);
  }

  navigateTo(path: string) {
    this.activeRoute.set(path);
    this.loading.set(true);
    // With withHashLocation() in Spike, change the hash to navigate in-place.
    // Same origin (served by Angular dev server), so contentWindow access is safe.
    const frame = this.themeFrame()?.nativeElement;
    if (frame) {
      const theme = this.selectedTheme();
      if (theme) {
        const hash = path ? `#/${path}` : '#/';
        const url = `/themes/${theme.assetPath}/index.html${hash}`;
        frame.src = url;
      }
    }
  }

  onIframeLoad() {
    this.loading.set(false);
    // No target-stripping needed — the sandbox attribute (without allow-popups)
    // silently blocks all target="_blank" / window.open() at the browser level.
    // Stripping targets would confuse Angular Router's internal route matching.
  }

  reloadIframe() {
    this.loading.set(true);
    const frame = this.themeFrame()?.nativeElement;
    if (frame) {
      frame.src = frame.src;
    }
  }

  openExternal() {
    const theme = this.selectedTheme();
    if (theme) {
      window.open(`/themes/${theme.assetPath}/index.html`, '_blank');
    }
  }
}
