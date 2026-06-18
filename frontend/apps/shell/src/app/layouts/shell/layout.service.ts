import { Injectable, signal, computed } from '@angular/core';

export interface LayoutConfig {
  menuMode: 'static' | 'overlay';
  darkTheme: boolean;
}

interface LayoutState {
  staticMenuDesktopInactive: boolean;
  overlayMenuActive: boolean;
  mobileMenuActive: boolean;
  menuHoverActive: boolean;
}

@Injectable({ providedIn: 'root' })
export class LayoutService {
  layoutConfig = signal<LayoutConfig>({
    menuMode: 'static',
    darkTheme: false,
  });

  layoutState = signal<LayoutState>({
    staticMenuDesktopInactive: false,
    overlayMenuActive: false,
    mobileMenuActive: false,
    menuHoverActive: false,
  });

  isSidebarActive = computed(
    () => this.layoutState().overlayMenuActive || this.layoutState().mobileMenuActive,
  );

  isOverlay = computed(() => this.layoutConfig().menuMode === 'overlay');

  onMenuToggle(): void {
    if (this.isOverlay()) {
      this.layoutState.update((s) => ({ ...s, overlayMenuActive: !s.overlayMenuActive }));
    }
    if (this.isDesktop()) {
      this.layoutState.update((s) => ({
        ...s,
        staticMenuDesktopInactive: !s.staticMenuDesktopInactive,
      }));
    } else {
      this.layoutState.update((s) => ({ ...s, mobileMenuActive: !s.mobileMenuActive }));
    }
  }

  closeMobileMenu(): void {
    this.layoutState.update((s) => ({ ...s, mobileMenuActive: false, overlayMenuActive: false }));
  }

  isDesktop(): boolean {
    return window.innerWidth > 991;
  }
}
