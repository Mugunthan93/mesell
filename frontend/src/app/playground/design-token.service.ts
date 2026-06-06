/**
 * DesignTokenService — SSOT for all design token candidates
 * Persists active tokens to localStorage.
 * Pending queue: pre-loaded from Playwright scraping session + fetch scrapes.
 */
import { Injectable, signal, computed, effect } from '@angular/core';

export type TokenCategory = '1.1' | '1.2' | '1.3' | '1.4' | '1.5' | '1.6'
  | '1.10' | '1.11' | '1.12' | '1.13' | '1.14';
export type TokenStatus   = 'active' | 'archived';
export type TokenSource   = 'seed' | 'scraped' | 'manual';

export interface DesignToken {
  id:          string;
  category:    TokenCategory;
  name:        string;
  source:      TokenSource;
  sourceUrl?:  string;
  status:      TokenStatus;
  addedAt:     string;
  // 1.1 & 1.2
  hex?:        string;
  onColor?:    string;
  // 1.3
  bg?:         string;
  surface?:    string;
  surfaceVar?: string;
  border?:     string;
  textColor?:  string;
  textMid?:    string;
  stops?:      string[];
  // 1.4
  cssFamily?:  string;
  indicType?:  'native' | 'pair';
  // 1.5
  cssClass?:   string;
  iconType?:   'material' | 'svg';
  dep?:        string;
  strokeWidth?: number;
  // 1.6 Motion
  duration?:    string;   // '150ms', '300ms'
  easing?:      string;   // 'cubic-bezier(0.4, 0, 0.2, 1)'
  motionLabel?: string;   // 'Color + shadow', 'All properties', 'Panel reveal' — also reused for radius descriptions (1.10)

  // 1.10 Border Radius
  radiusValue?: string;   // e.g. '0.375rem', '9999px'
  radiusPx?:    number;   // pixel equivalent for display
  radiusName?:  string;   // 'none' | 'sm' | 'base' | 'md' | 'lg' | 'xl' | 'full'

  // 1.11 Elevation / Shadow
  shadowValue?: string;   // full box-shadow CSS string
  shadowLabel?: string;   // 'card' | 'dropdown' | 'overlay' | 'focus-ring'

  // 1.12 State Color Variants
  stateColor?:   string;  // 'primary' | 'success' | 'warning' | 'error' | 'info'
  stateVariant?: string;  // 'active' | 'light' | 'clarity'

  // 1.13 Typography Scale
  fontWeight?:       number; // 400 | 500 | 600 | 700
  leading?:          string; // '1.2' | '1.5' | '1.75'
  tracking?:         string; // '-0.025em' | '0em' | '0.025em'
  typographyLabel?:  string;

  // 1.14 Layout Dimensions
  layoutValue?:   string; // '240px', '60px', etc.
  layoutLabel?:   string; // 'sidebar-width' | 'header-height' | etc.
  layoutCssVar?:  string; // '--mee-layout-sidebar-width'
}

export type ScrapeCandidate = Omit<DesignToken, 'id' | 'status' | 'addedAt'>;

// ── ThemeTemplate — scraped theme JSON contract ────────────────────────────

export interface ThemeComponentStyle {
  borderRadius?: string;
  boxShadow?: string;
  background?: string;
  color?: string;
  padding?: string;
  fontSize?: string;
  fontWeight?: number | string;
  lineHeight?: string;
  border?: string;
  transition?: string;
  [key: string]: string | number | undefined;
}

export interface ThemeTemplate {
  _meta: {
    themeId: string;           // 'metronic' | 'velzon' | 'adminto' etc.
    themeName: string;         // 'Metronic Tailwind v4'
    sourceUrl: string;         // 'https://keenthemes.com/metronic/tailwind/demo1/'
    scrapedAt: string;         // ISO date
    pagesVisited: string[];
    componentsFound: number;
  };
  tokens: {
    colors: {
      primary?: string;
      'primary-active'?: string;
      'primary-light'?: string;
      'primary-clarity'?: string;
      secondary?: string;
      'secondary-active'?: string;
      'secondary-light'?: string;
      success?: string;
      'success-active'?: string;
      'success-light'?: string;
      'success-clarity'?: string;
      warning?: string;
      'warning-active'?: string;
      'warning-light'?: string;
      'warning-clarity'?: string;
      danger?: string;
      'danger-active'?: string;
      'danger-light'?: string;
      'danger-clarity'?: string;
      info?: string;
      'info-active'?: string;
      'info-light'?: string;
      'info-clarity'?: string;
      'body-bg'?: string;
      'body-color'?: string;
      muted?: string;
      border?: string;
      [key: string]: string | undefined;
    };
    typography: {
      fontFamily?: string;
      bodySize?: string;
      bodyWeight?: number;
      bodyLineHeight?: string;
      headingColor?: string;
      mutedColor?: string;
      scale?: Record<string, string>;
    };
    radius: {
      btn?: string;
      card?: string;
      input?: string;
      modal?: string;
      dropdown?: string;
      badge?: string;
      base?: string;
    };
    shadow: {
      card?: string;
      modal?: string;
      dropdown?: string;
      'focus-ring'?: string;
    };
    layout: {
      sidebarWidth?: string;
      sidebarCollapsedWidth?: string;
      headerHeight?: string;
      toolbarHeight?: string;
      contentMaxWidth?: string;
    };
    animation: {
      durationFast?: string;
      durationBase?: string;
      durationSlow?: string;
      easingBase?: string;
      easingEnter?: string;
      easingExit?: string;
    };
    spacing: Record<string, string>;
    zIndex: Record<string, number>;
    allCssVars: Record<string, string>;
  };
  components: {
    button?: ThemeComponentStyle;
    input?: ThemeComponentStyle;
    card?: ThemeComponentStyle;
    badge?: ThemeComponentStyle;
    alert?: ThemeComponentStyle;
    table?: ThemeComponentStyle;
    modal?: ThemeComponentStyle;
    dropdown?: ThemeComponentStyle;
    tabs?: ThemeComponentStyle;
    progress?: ThemeComponentStyle;
    avatar?: ThemeComponentStyle;
    sidebar?: ThemeComponentStyle;
    navbar?: ThemeComponentStyle;
    [key: string]: ThemeComponentStyle | undefined;
  };
  componentInventory: Array<{
    name: string;
    selector: string;
    pagesFound: string[];
    category: string;  // 'layout' | 'form' | 'data' | 'feedback' | 'navigation' | 'display'
  }>;
}

const STORAGE_KEY = 'meesell-design-tokens-v1';

const SEED: DesignToken[] = [
  // ── 1.1 Primary (9) ───────────────────────────────────────────────────────
  { id:'seed-1.1-1', category:'1.1', name:'Razorpay Navy',         source:'seed', status:'active', addedAt:'2026-06-05', hex:'#0F1641', onColor:'#FFFFFF' },
  { id:'seed-1.1-2', category:'1.1', name:'Khatabook Orange',      source:'seed', status:'active', addedAt:'2026-06-05', hex:'#F36F21', onColor:'#FFFFFF' },
  { id:'seed-1.1-3', category:'1.1', name:'Vyapar Amber',          source:'seed', status:'active', addedAt:'2026-06-05', hex:'#FF8200', onColor:'#000000' },
  { id:'seed-1.1-4', category:'1.1', name:'Zoho Rust-Red',         source:'seed', status:'active', addedAt:'2026-06-05', hex:'#C8102E', onColor:'#FFFFFF' },
  { id:'seed-1.1-5', category:'1.1', name:'Freshworks Teal',       source:'seed', status:'active', addedAt:'2026-06-05', hex:'#173B45', onColor:'#FFFFFF' },
  { id:'seed-1.1-6', category:'1.1', name:'Lightspeed Terracotta', source:'seed', status:'active', addedAt:'2026-06-05', hex:'#E25F2A', onColor:'#FFFFFF' },
  { id:'seed-1.1-7', category:'1.1', name:'BharatPe Navy',         source:'seed', status:'active', addedAt:'2026-06-05', hex:'#0F2B6E', onColor:'#FFFFFF' },
  { id:'seed-1.1-8', category:'1.1', name:'OkCredit Gold',         source:'seed', status:'active', addedAt:'2026-06-05', hex:'#D9A14B', onColor:'#000000' },
  { id:'seed-1.1-9', category:'1.1', name:'Notion No-Chromatic',   source:'seed', status:'active', addedAt:'2026-06-05', hex:'#37352F', onColor:'#FFFFFF' },
  // ── 1.2 Secondary (8) ─────────────────────────────────────────────────────
  { id:'seed-1.2-1', category:'1.2', name:'IBM Carbon Blue',       source:'seed', status:'active', addedAt:'2026-06-05', hex:'#0F62FE', onColor:'#FFFFFF' },
  { id:'seed-1.2-2', category:'1.2', name:'Material 3 Blue',       source:'seed', status:'active', addedAt:'2026-06-05', hex:'#1D4ED8', onColor:'#FFFFFF' },
  { id:'seed-1.2-3', category:'1.2', name:'Atlassian Teal',        source:'seed', status:'active', addedAt:'2026-06-05', hex:'#00B8D9', onColor:'#000000' },
  { id:'seed-1.2-4', category:'1.2', name:'Tailwind Slate-700',    source:'seed', status:'active', addedAt:'2026-06-05', hex:'#334155', onColor:'#FFFFFF' },
  { id:'seed-1.2-5', category:'1.2', name:'Polaris Green',         source:'seed', status:'active', addedAt:'2026-06-05', hex:'#008060', onColor:'#FFFFFF' },
  { id:'seed-1.2-6', category:'1.2', name:'GitHub Primer Blue',    source:'seed', status:'active', addedAt:'2026-06-05', hex:'#0969DA', onColor:'#FFFFFF' },
  { id:'seed-1.2-7', category:'1.2', name:'Tailwind Emerald',      source:'seed', status:'active', addedAt:'2026-06-05', hex:'#047857', onColor:'#FFFFFF' },
  { id:'seed-1.2-8', category:'1.2', name:'Carbon Cool Gray 90',   source:'seed', status:'active', addedAt:'2026-06-05', hex:'#393939', onColor:'#FFFFFF' },
  // ── 1.3 Surface (7) ───────────────────────────────────────────────────────
  { id:'seed-1.3-1', category:'1.3', name:'Carbon Cool Gray',   source:'seed', status:'active', addedAt:'2026-06-05', bg:'#F4F4F4', surface:'#FFFFFF', surfaceVar:'#E8E8E8', border:'#C6C6C6', textColor:'#161616', textMid:'#6F6F6F', stops:['#F4F4F4','#FFFFFF','#E0E0E0','#6F6F6F','#161616'] },
  { id:'seed-1.3-2', category:'1.3', name:'Atlassian Neutral',  source:'seed', status:'active', addedAt:'2026-06-05', bg:'#F7F8F9', surface:'#FFFFFF', surfaceVar:'#EBECF0', border:'#DCDFE4', textColor:'#172B4D', textMid:'#626F86', stops:['#F7F8F9','#FFFFFF','#DCDFE4','#626F86','#172B4D'] },
  { id:'seed-1.3-3', category:'1.3', name:'Polaris Warm',       source:'seed', status:'active', addedAt:'2026-06-05', bg:'#F6F6F7', surface:'#FFFFFF', surfaceVar:'#F1F2F3', border:'#E1E3E5', textColor:'#202223', textMid:'#6D7175', stops:['#F6F6F7','#FFFFFF','#E1E3E5','#6D7175','#202223'] },
  { id:'seed-1.3-4', category:'1.3', name:'GitHub Primer',      source:'seed', status:'active', addedAt:'2026-06-05', bg:'#F6F8FA', surface:'#FFFFFF', surfaceVar:'#EAEEF2', border:'#D0D7DE', textColor:'#1F2328', textMid:'#57606A', stops:['#F6F8FA','#FFFFFF','#D0D7DE','#57606A','#1F2328'] },
  { id:'seed-1.3-5', category:'1.3', name:'Material 3 Tonal',   source:'seed', status:'active', addedAt:'2026-06-05', bg:'#F4EFF4', surface:'#FFFBFE', surfaceVar:'#EDE7F6', border:'#CAC4D0', textColor:'#1C1B1F', textMid:'#49454F', stops:['#F4EFF4','#FFFBFE','#CAC4D0','#49454F','#1C1B1F'] },
  { id:'seed-1.3-6', category:'1.3', name:'Tailwind Stone',     source:'seed', status:'active', addedAt:'2026-06-05', bg:'#FAFAF9', surface:'#FFFFFF', surfaceVar:'#F5F5F4', border:'#E7E5E4', textColor:'#1C1917', textMid:'#78716C', stops:['#FAFAF9','#FFFFFF','#E7E5E4','#78716C','#1C1917'] },
  { id:'seed-1.3-7', category:'1.3', name:'Notion Warm Cream',  source:'seed', status:'active', addedAt:'2026-06-05', bg:'#F7F6F3', surface:'#FFFFFF', surfaceVar:'#EEECE9', border:'#E9E9E7', textColor:'#37352F', textMid:'#9B9A97', stops:['#F7F6F3','#FFFFFF','#E9E9E7','#9B9A97','#37352F'] },
  // ── 1.4 Typeface (8) ──────────────────────────────────────────────────────
  { id:'seed-1.4-1', category:'1.4', name:'Inter',             source:'seed', status:'active', addedAt:'2026-06-05', cssFamily:"'Inter', system-ui, sans-serif",              indicType:'pair' },
  { id:'seed-1.4-2', category:'1.4', name:'Plus Jakarta Sans', source:'seed', status:'active', addedAt:'2026-06-05', cssFamily:"'Plus Jakarta Sans', system-ui, sans-serif",  indicType:'pair' },
  { id:'seed-1.4-3', category:'1.4', name:'DM Sans',           source:'seed', status:'active', addedAt:'2026-06-05', cssFamily:"'DM Sans', system-ui, sans-serif",             indicType:'pair' },
  { id:'seed-1.4-4', category:'1.4', name:'Manrope',           source:'seed', status:'active', addedAt:'2026-06-05', cssFamily:"'Manrope', system-ui, sans-serif",             indicType:'pair' },
  { id:'seed-1.4-5', category:'1.4', name:'Be Vietnam Pro',    source:'seed', status:'active', addedAt:'2026-06-05', cssFamily:"'Be Vietnam Pro', system-ui, sans-serif",      indicType:'pair' },
  { id:'seed-1.4-6', category:'1.4', name:'Noto Sans',         source:'seed', status:'active', addedAt:'2026-06-05', cssFamily:"'Noto Sans', system-ui, sans-serif",           indicType:'native' },
  { id:'seed-1.4-7', category:'1.4', name:'Hanken Grotesk',    source:'seed', status:'active', addedAt:'2026-06-05', cssFamily:"'Hanken Grotesk', system-ui, sans-serif",      indicType:'pair' },
  { id:'seed-1.4-8', category:'1.4', name:'Public Sans',       source:'seed', status:'active', addedAt:'2026-06-05', cssFamily:"'Public Sans', system-ui, sans-serif",         indicType:'pair' },
  // ── 1.5 Icons (6) ─────────────────────────────────────────────────────────
  { id:'seed-1.5-1', category:'1.5', name:'Material Outlined', source:'seed', status:'active', addedAt:'2026-06-05', cssClass:'ms-outlined', iconType:'material', dep:'No dep (Angular default)',  strokeWidth:2 },
  { id:'seed-1.5-2', category:'1.5', name:'Material Rounded',  source:'seed', status:'active', addedAt:'2026-06-05', cssClass:'ms-rounded',  iconType:'material', dep:'No dep (warmer feel)',      strokeWidth:2 },
  { id:'seed-1.5-3', category:'1.5', name:'Material Sharp',    source:'seed', status:'active', addedAt:'2026-06-05', cssClass:'ms-sharp',    iconType:'material', dep:'No dep (crispest)',         strokeWidth:2 },
  { id:'seed-1.5-4', category:'1.5', name:'Phosphor',          source:'seed', status:'active', addedAt:'2026-06-05', cssClass:'',            iconType:'svg',      dep:'+80KB dep · 6 weights',     strokeWidth:1.5 },
  { id:'seed-1.5-5', category:'1.5', name:'Lucide',            source:'seed', status:'active', addedAt:'2026-06-05', cssClass:'',            iconType:'svg',      dep:'+dep · single weight',      strokeWidth:2 },
  { id:'seed-1.5-6', category:'1.5', name:'Tabler',            source:'seed', status:'active', addedAt:'2026-06-05', cssClass:'',            iconType:'svg',      dep:'+dep · outlined + filled',  strokeWidth:1.5 },
  // ── 1.6 Motion (5) ────────────────────────────────────────────────────────
  { id:'seed-1.6-1', category:'1.6', name:'Instant',   source:'seed', status:'active', addedAt:'2026-06-06', duration:'75ms',  easing:'ease',                          motionLabel:'Focus ring, micro' },
  { id:'seed-1.6-2', category:'1.6', name:'Fast',      source:'seed', status:'active', addedAt:'2026-06-06', duration:'150ms', easing:'cubic-bezier(0.4, 0, 0.2, 1)', motionLabel:'Button hover, chip tap' },
  { id:'seed-1.6-3', category:'1.6', name:'Standard',  source:'seed', status:'active', addedAt:'2026-06-06', duration:'200ms', easing:'cubic-bezier(0.4, 0, 0.2, 1)', motionLabel:'State change, toggle' },
  { id:'seed-1.6-4', category:'1.6', name:'Moderate',  source:'seed', status:'active', addedAt:'2026-06-06', duration:'300ms', easing:'cubic-bezier(0.4, 0, 0.2, 1)', motionLabel:'Panel slide, dropdown' },
  { id:'seed-1.6-5', category:'1.6', name:'Page',      source:'seed', status:'active', addedAt:'2026-06-06', duration:'450ms', easing:'cubic-bezier(0, 0, 0.2, 1)',    motionLabel:'Route, full-page' },

  // ── 1.10 Border Radius (7) ────────────────────────────────────────────────
  { id:'seed-1.10-1', category:'1.10', name:'Radius None',  source:'seed', status:'active', addedAt:'2026-06-06', radiusValue:'0',        radiusPx:0,    radiusName:'none',  motionLabel:'Sharp — no rounding' },
  { id:'seed-1.10-2', category:'1.10', name:'Radius SM',    source:'seed', status:'active', addedAt:'2026-06-06', radiusValue:'0.25rem',  radiusPx:4,    radiusName:'sm',    motionLabel:'Badge, tag, tooltip' },
  { id:'seed-1.10-3', category:'1.10', name:'Radius Base',  source:'seed', status:'active', addedAt:'2026-06-06', radiusValue:'0.375rem', radiusPx:6,    radiusName:'base',  motionLabel:'Button, input, chip' },
  { id:'seed-1.10-4', category:'1.10', name:'Radius MD',    source:'seed', status:'active', addedAt:'2026-06-06', radiusValue:'0.5rem',   radiusPx:8,    radiusName:'md',    motionLabel:'Dropdown, popover' },
  { id:'seed-1.10-5', category:'1.10', name:'Radius LG',    source:'seed', status:'active', addedAt:'2026-06-06', radiusValue:'0.625rem', radiusPx:10,   radiusName:'lg',    motionLabel:'Card, modal, drawer' },
  { id:'seed-1.10-6', category:'1.10', name:'Radius XL',    source:'seed', status:'active', addedAt:'2026-06-06', radiusValue:'1rem',     radiusPx:16,   radiusName:'xl',    motionLabel:'Full-bleed panel' },
  { id:'seed-1.10-7', category:'1.10', name:'Radius Full',  source:'seed', status:'active', addedAt:'2026-06-06', radiusValue:'9999px',   radiusPx:9999, radiusName:'full',  motionLabel:'Pill button, avatar' },

  // ── 1.11 Elevation / Shadow (9) ───────────────────────────────────────────
  { id:'seed-1.11-1', category:'1.11', name:'Shadow None',     source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'none',                                              shadowLabel:'Flat — no elevation' },
  { id:'seed-1.11-2', category:'1.11', name:'Shadow Card',     source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'0px 3px 4px 0px rgba(0,0,0,0.04)',                shadowLabel:'Subtle card lift' },
  { id:'seed-1.11-3', category:'1.11', name:'Shadow MD',       source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'0px 4px 12px 0px rgba(0,0,0,0.08)',               shadowLabel:'Raised card, sidebar' },
  { id:'seed-1.11-4', category:'1.11', name:'Shadow Dropdown', source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'0px 4px 20px 0px rgba(0,0,0,0.08)',               shadowLabel:'Menu, select, popover' },
  { id:'seed-1.11-5', category:'1.11', name:'Shadow Overlay',  source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'0px 0px 30px 0px rgba(0,0,0,0.12)',               shadowLabel:'Modal, drawer, sheet' },
  { id:'seed-1.11-6', category:'1.11', name:'Shadow XL',       source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'0px 20px 60px 0px rgba(0,0,0,0.15)',              shadowLabel:'Floating action panel' },
  { id:'seed-1.11-7', category:'1.11', name:'Ring — Primary',  source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'0 0 0 2px #F36F21',                               shadowLabel:'Keyboard focus ring (primary)' },
  { id:'seed-1.11-8', category:'1.11', name:'Ring — Neutral',  source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'0 0 0 2px rgba(0,0,0,0.15)',                      shadowLabel:'Keyboard focus ring (subtle)' },
  { id:'seed-1.11-9', category:'1.11', name:'Ring — Error',    source:'seed', status:'active', addedAt:'2026-06-06', shadowValue:'0 0 0 2px #DC2626',                               shadowLabel:'Invalid input focus ring' },

  // ── 1.12 State Color Variants (15) ────────────────────────────────────────
  { id:'seed-1.12-1',  category:'1.12', name:'Primary Active',   source:'seed', status:'active', addedAt:'2026-06-06', hex:'#D95E1B', onColor:'#FFFFFF', stateColor:'primary', stateVariant:'active' },
  { id:'seed-1.12-2',  category:'1.12', name:'Primary Light',    source:'seed', status:'active', addedAt:'2026-06-06', hex:'#FFF3EC', onColor:'#D95E1B', stateColor:'primary', stateVariant:'light' },
  { id:'seed-1.12-3',  category:'1.12', name:'Primary Clarity',  source:'seed', status:'active', addedAt:'2026-06-06', hex:'#FFE4CC', onColor:'#D95E1B', stateColor:'primary', stateVariant:'clarity' },
  { id:'seed-1.12-4',  category:'1.12', name:'Success Active',   source:'seed', status:'active', addedAt:'2026-06-06', hex:'#15803D', onColor:'#FFFFFF', stateColor:'success',  stateVariant:'active' },
  { id:'seed-1.12-5',  category:'1.12', name:'Success Light',    source:'seed', status:'active', addedAt:'2026-06-06', hex:'#F0FDF4', onColor:'#15803D', stateColor:'success',  stateVariant:'light' },
  { id:'seed-1.12-6',  category:'1.12', name:'Success Clarity',  source:'seed', status:'active', addedAt:'2026-06-06', hex:'#DCFCE7', onColor:'#15803D', stateColor:'success',  stateVariant:'clarity' },
  { id:'seed-1.12-7',  category:'1.12', name:'Warning Active',   source:'seed', status:'active', addedAt:'2026-06-06', hex:'#B45309', onColor:'#FFFFFF', stateColor:'warning',  stateVariant:'active' },
  { id:'seed-1.12-8',  category:'1.12', name:'Warning Light',    source:'seed', status:'active', addedAt:'2026-06-06', hex:'#FFFBEB', onColor:'#B45309', stateColor:'warning',  stateVariant:'light' },
  { id:'seed-1.12-9',  category:'1.12', name:'Warning Clarity',  source:'seed', status:'active', addedAt:'2026-06-06', hex:'#FEF3C7', onColor:'#B45309', stateColor:'warning',  stateVariant:'clarity' },
  { id:'seed-1.12-10', category:'1.12', name:'Error Active',     source:'seed', status:'active', addedAt:'2026-06-06', hex:'#B91C1C', onColor:'#FFFFFF', stateColor:'error',    stateVariant:'active' },
  { id:'seed-1.12-11', category:'1.12', name:'Error Light',      source:'seed', status:'active', addedAt:'2026-06-06', hex:'#FFF1F2', onColor:'#B91C1C', stateColor:'error',    stateVariant:'light' },
  { id:'seed-1.12-12', category:'1.12', name:'Error Clarity',    source:'seed', status:'active', addedAt:'2026-06-06', hex:'#FFE4E6', onColor:'#B91C1C', stateColor:'error',    stateVariant:'clarity' },
  { id:'seed-1.12-13', category:'1.12', name:'Info Active',      source:'seed', status:'active', addedAt:'2026-06-06', hex:'#1D4ED8', onColor:'#FFFFFF', stateColor:'info',     stateVariant:'active' },
  { id:'seed-1.12-14', category:'1.12', name:'Info Light',       source:'seed', status:'active', addedAt:'2026-06-06', hex:'#EFF6FF', onColor:'#1D4ED8', stateColor:'info',     stateVariant:'light' },
  { id:'seed-1.12-15', category:'1.12', name:'Info Clarity',     source:'seed', status:'active', addedAt:'2026-06-06', hex:'#DBEAFE', onColor:'#1D4ED8', stateColor:'info',     stateVariant:'clarity' },

  // ── 1.13 Typography Scale (10) ────────────────────────────────────────────
  { id:'seed-1.13-1',  category:'1.13', name:'Weight Normal',    source:'seed', status:'active', addedAt:'2026-06-06', fontWeight:400, typographyLabel:'Body text, placeholder' },
  { id:'seed-1.13-2',  category:'1.13', name:'Weight Medium',    source:'seed', status:'active', addedAt:'2026-06-06', fontWeight:500, typographyLabel:'Label, nav item, chip' },
  { id:'seed-1.13-3',  category:'1.13', name:'Weight Semibold',  source:'seed', status:'active', addedAt:'2026-06-06', fontWeight:600, typographyLabel:'Button, subheading, badge' },
  { id:'seed-1.13-4',  category:'1.13', name:'Weight Bold',      source:'seed', status:'active', addedAt:'2026-06-06', fontWeight:700, typographyLabel:'Page heading, stat value' },
  { id:'seed-1.13-5',  category:'1.13', name:'Leading Tight',    source:'seed', status:'active', addedAt:'2026-06-06', leading:'1.2',  typographyLabel:'Heading, display text' },
  { id:'seed-1.13-6',  category:'1.13', name:'Leading Base',     source:'seed', status:'active', addedAt:'2026-06-06', leading:'1.5',  typographyLabel:'Body, paragraph' },
  { id:'seed-1.13-7',  category:'1.13', name:'Leading Relaxed',  source:'seed', status:'active', addedAt:'2026-06-06', leading:'1.75', typographyLabel:'Long-form content' },
  { id:'seed-1.13-8',  category:'1.13', name:'Tracking Tight',   source:'seed', status:'active', addedAt:'2026-06-06', tracking:'-0.025em', typographyLabel:'Large headings' },
  { id:'seed-1.13-9',  category:'1.13', name:'Tracking Normal',  source:'seed', status:'active', addedAt:'2026-06-06', tracking:'0em',      typographyLabel:'Body, labels' },
  { id:'seed-1.13-10', category:'1.13', name:'Tracking Wide',    source:'seed', status:'active', addedAt:'2026-06-06', tracking:'0.025em',  typographyLabel:'Caps, overline, badge' },

  // ── 1.14 Layout Dimensions (5) ────────────────────────────────────────────
  { id:'seed-1.14-1', category:'1.14', name:'Sidebar Width',     source:'seed', status:'active', addedAt:'2026-06-06', layoutValue:'240px',  layoutLabel:'Sidebar expanded',      layoutCssVar:'--mee-layout-sidebar-width' },
  { id:'seed-1.14-2', category:'1.14', name:'Sidebar Collapsed', source:'seed', status:'active', addedAt:'2026-06-06', layoutValue:'64px',   layoutLabel:'Sidebar collapsed',     layoutCssVar:'--mee-layout-sidebar-collapsed' },
  { id:'seed-1.14-3', category:'1.14', name:'Header Height',     source:'seed', status:'active', addedAt:'2026-06-06', layoutValue:'60px',   layoutLabel:'Top navbar',            layoutCssVar:'--mee-layout-header-height' },
  { id:'seed-1.14-4', category:'1.14', name:'Toolbar Height',    source:'seed', status:'active', addedAt:'2026-06-06', layoutValue:'52px',   layoutLabel:'Sub-toolbar / tab bar', layoutCssVar:'--mee-layout-toolbar-height' },
  { id:'seed-1.14-5', category:'1.14', name:'Content Max Width', source:'seed', status:'active', addedAt:'2026-06-06', layoutValue:'1200px', layoutLabel:'Content area cap',      layoutCssVar:'--mee-layout-content-max-width' },
];

/**
 * Candidates pre-loaded from Playwright browser session.
 * Shown as pending (awaiting approval) on first page load.
 * Sources: Metronic (Tailwind), Velzon (Bootstrap), Adminto (Bootstrap).
 */
const PLAYWRIGHT_SCRAPED: ScrapeCandidate[] = [
  // ── Metronic — Tailwind CSS · keenthemes.com ───────────────────────────
  { category:'1.1', name:'Metronic Blue',          source:'scraped', sourceUrl:'https://keenthemes.com/metronic/tailwind/demo1/', hex:'#3B82F6', onColor:'#FFFFFF' },
  { category:'1.2', name:'Metronic Violet',        source:'scraped', sourceUrl:'https://keenthemes.com/metronic/tailwind/demo1/', hex:'#7C3AED', onColor:'#FFFFFF' },
  { category:'1.3', name:'Metronic Zinc',          source:'scraped', sourceUrl:'https://keenthemes.com/metronic/tailwind/demo1/', bg:'#f4f4f5', surface:'#ffffff', surfaceVar:'#e4e4e7', border:'#e4e4e7', textColor:'#09090b', textMid:'#71717a', stops:['#f4f4f5','#ffffff','#e4e4e7','#71717a','#09090b'] },
  { category:'1.6', name:'Metronic Fast',          source:'scraped', sourceUrl:'https://keenthemes.com/metronic/tailwind/demo1/', duration:'150ms', easing:'cubic-bezier(0.4, 0, 0.2, 1)', motionLabel:'Color + shadow (Tailwind default)' },
  { category:'1.6', name:'Metronic All-Props',     source:'scraped', sourceUrl:'https://keenthemes.com/metronic/tailwind/demo1/', duration:'300ms', easing:'cubic-bezier(0.4, 0, 0.2, 1)', motionLabel:'Color, opacity, shadow, transform' },
  // ── Velzon — Bootstrap 5 · themesbrand.com ────────────────────────────
  { category:'1.1', name:'Velzon Deep Indigo',     source:'scraped', sourceUrl:'https://themesbrand.com/velzon/html/default/', hex:'#405189', onColor:'#FFFFFF' },
  { category:'1.2', name:'Velzon Bright Blue',     source:'scraped', sourceUrl:'https://themesbrand.com/velzon/html/default/', hex:'#3577F1', onColor:'#FFFFFF' },
  { category:'1.3', name:'Velzon Lavender',        source:'scraped', sourceUrl:'https://themesbrand.com/velzon/html/default/', bg:'#f3f3f9', surface:'#ffffff', surfaceVar:'#eff2f7', border:'#e9ebec', textColor:'#212529', textMid:'#6d7080', stops:['#f3f3f9','#ffffff','#e9ebec','#6d7080','#212529'] },
  { category:'1.4', name:'Poppins',                source:'scraped', sourceUrl:'https://themesbrand.com/velzon/html/default/', cssFamily:"'Poppins', system-ui, sans-serif", indicType:'pair' },
  // ── Adminto — Bootstrap 5 · coderthemes.com ───────────────────────────
  { category:'1.1', name:'Adminto Sky Blue',       source:'scraped', sourceUrl:'https://coderthemes.com/adminto/layouts/index.html', hex:'#188AE2', onColor:'#FFFFFF' },
  { category:'1.2', name:'Adminto Indigo',         source:'scraped', sourceUrl:'https://coderthemes.com/adminto/layouts/index.html', hex:'#5B69BC', onColor:'#FFFFFF' },
  { category:'1.3', name:'Adminto Soft Blue-Gray', source:'scraped', sourceUrl:'https://coderthemes.com/adminto/layouts/index.html', bg:'#f0f4f7', surface:'#ffffff', surfaceVar:'#f6f7fb', border:'#e7e9eb', textColor:'#4c4c5c', textMid:'#8a969c', stops:['#f0f4f7','#ffffff','#e7e9eb','#8a969c','#4c4c5c'] },
];

@Injectable({ providedIn: 'root' })
export class DesignTokenService {
  private _tokens  = signal<DesignToken[]>(this.hydrate());
  private _pending = signal<ScrapeCandidate[]>([]);

  readonly tokens              = this._tokens.asReadonly();
  readonly pendingCandidates   = this._pending.asReadonly();

  readonly activeByCategory = computed(() => {
    const all = this._tokens();
    return {
      '1.1':  all.filter(t => t.category === '1.1'  && t.status === 'active'),
      '1.2':  all.filter(t => t.category === '1.2'  && t.status === 'active'),
      '1.3':  all.filter(t => t.category === '1.3'  && t.status === 'active'),
      '1.4':  all.filter(t => t.category === '1.4'  && t.status === 'active'),
      '1.5':  all.filter(t => t.category === '1.5'  && t.status === 'active'),
      '1.6':  all.filter(t => t.category === '1.6'  && t.status === 'active'),
      '1.10': all.filter(t => t.category === '1.10' && t.status === 'active'),
      '1.11': all.filter(t => t.category === '1.11' && t.status === 'active'),
      '1.12': all.filter(t => t.category === '1.12' && t.status === 'active'),
      '1.13': all.filter(t => t.category === '1.13' && t.status === 'active'),
      '1.14': all.filter(t => t.category === '1.14' && t.status === 'active'),
    };
  });

  constructor() {
    // Persist active tokens
    effect(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this._tokens()));
    });
    // Seed pending with Playwright-scraped candidates, filtering out already-active duplicates
    this.resetPending();
  }

  /** Reset pending queue to Playwright-scraped candidates (minus already-approved). */
  resetPending(): void {
    const activeNames = new Set(
      this._tokens().map(t => `${t.category}::${t.name.toLowerCase()}`)
    );
    const filtered = PLAYWRIGHT_SCRAPED.filter(
      c => !activeNames.has(`${c.category}::${c.name.toLowerCase()}`)
    );
    this._pending.set(filtered);
  }

  // ── Pending queue management ─────────────────────────────────────────────

  /** Push new candidates into the pending queue (from URL scrape or manual). */
  addPending(candidates: ScrapeCandidate[]): void {
    this._pending.update(p => [...p, ...candidates]);
  }

  /** Approve a single pending item by index, applying an optional category override. */
  approvePending(idx: number, categoryOverride?: TokenCategory): void {
    const items = this._pending();
    const item = items[idx];
    if (!item) return;
    const toAdd: ScrapeCandidate = categoryOverride ? { ...item, category: categoryOverride } : item;
    this.addActive([toAdd]);
    this._pending.update(p => p.filter((_, i) => i !== idx));
  }

  /** Remove a pending item without adding it to active. */
  skipPending(idx: number): void {
    this._pending.update(p => p.filter((_, i) => i !== idx));
  }

  /** Approve every pending item, applying per-index category overrides. */
  approveAllPending(overrides: Partial<Record<number, TokenCategory>> = {}): void {
    const items = this._pending();
    const finals = items.map((item, i) =>
      overrides[i] ? { ...item, category: overrides[i]! } : item
    );
    this.addActive(finals);
    this._pending.set([]);
  }

  clearPending(): void { this._pending.set([]); }

  // ── Active token management ───────────────────────────────────────────────

  /** Add approved candidates directly as active tokens. */
  addActive(candidates: ScrapeCandidate[]): void {
    const now = new Date().toISOString();
    const newTokens: DesignToken[] = candidates.map((c, i) => ({
      ...c,
      id: `scraped-${Date.now()}-${i}`,
      status: 'active' as TokenStatus,
      addedAt: now,
    }));
    this._tokens.update(curr => [...curr, ...newTokens]);
  }

  archive(id: string): void {
    this._tokens.update(curr =>
      curr.map(t => t.id === id ? { ...t, status: 'archived' as TokenStatus } : t)
    );
  }

  resetToSeed(): void {
    this._tokens.set([...SEED]);
    this.resetPending();
  }

  // ── ThemeTemplate ingestion ───────────────────────────────────────────────

  /** Tracks which theme IDs have been imported in this session. */
  readonly loadedThemeIds = signal<string[]>([]);

  /**
   * Ingest a scraped ThemeTemplate JSON and convert it into DesignToken entries.
   * Tokens with IDs that already exist in the active list are silently skipped
   * (deduplication by id — safe to call multiple times with the same template).
   */
  importThemeTemplate(template: ThemeTemplate): void {
    const { themeId, themeName, sourceUrl, scrapedAt } = template._meta;
    const base = {
      source: 'scraped' as const,
      status: 'active' as const,
      sourceUrl,
      addedAt: scrapedAt,
    };
    const tokens: DesignToken[] = [];
    const t = template.tokens;

    // 1.1 Primary Color
    if (t.colors.primary) {
      tokens.push({
        ...base,
        id: `${themeId}-1.1-primary`,
        category: '1.1',
        name: `${themeName} Primary`,
        hex: t.colors.primary,
        onColor: '#FFFFFF',
      });
    }

    // 1.2 Secondary Color
    if (t.colors.secondary) {
      tokens.push({
        ...base,
        id: `${themeId}-1.2-secondary`,
        category: '1.2',
        name: `${themeName} Secondary`,
        hex: t.colors.secondary,
        onColor: '#FFFFFF',
      });
    }

    // 1.3 Surface Palette — derive from body-bg + border
    if (t.colors['body-bg'] || t.colors.border) {
      tokens.push({
        ...base,
        id: `${themeId}-1.3-surface`,
        category: '1.3',
        name: `${themeName} Surface`,
        bg: t.colors['body-bg'] ?? '#F9FAFB',
        surface: '#FFFFFF',
        surfaceVar: '#F3F4F6',
        border: t.colors.border ?? '#E5E7EB',
        textColor: t.colors['body-color'] ?? '#111827',
        textMid: t.colors.muted ?? '#6B7280',
        stops: [
          t.colors['body-bg'] ?? '#F9FAFB',
          '#FFFFFF',
          t.colors.border ?? '#E5E7EB',
        ],
      });
    }

    // 1.4 Typeface
    if (t.typography.fontFamily) {
      tokens.push({
        ...base,
        id: `${themeId}-1.4-font`,
        category: '1.4',
        name: `${themeName} Font`,
        cssFamily: t.typography.fontFamily,
      });
    }

    // 1.6 Motion — durationBase + easingBase
    if (t.animation.durationBase || t.animation.easingBase) {
      tokens.push({
        ...base,
        id: `${themeId}-1.6-motion`,
        category: '1.6',
        name: `${themeName} Motion`,
        duration: t.animation.durationBase ?? '150ms',
        easing: t.animation.easingBase ?? 'ease',
      });
    }

    // 1.10 Border Radius — card radius as representative
    if (t.radius.card) {
      const pxVal = parseFloat(t.radius.card) * (t.radius.card.includes('rem') ? 16 : 1);
      tokens.push({
        ...base,
        id: `${themeId}-1.10-radius`,
        category: '1.10',
        name: `${themeName} Radius`,
        radiusValue: t.radius.card,
        radiusPx: pxVal,
        radiusName: 'card',
      });
    }
    if (t.radius.btn && t.radius.btn !== t.radius.card) {
      const pxVal = parseFloat(t.radius.btn) * (t.radius.btn.includes('rem') ? 16 : 1);
      tokens.push({
        ...base,
        id: `${themeId}-1.10-radius-btn`,
        category: '1.10',
        name: `${themeName} Btn Radius`,
        radiusValue: t.radius.btn,
        radiusPx: pxVal,
        radiusName: 'btn',
      });
    }

    // 1.11 Elevation — card, modal, dropdown shadows
    if (t.shadow.card) {
      tokens.push({
        ...base,
        id: `${themeId}-1.11-shadow-card`,
        category: '1.11',
        name: `${themeName} Card Shadow`,
        shadowValue: t.shadow.card,
        shadowLabel: 'card',
      });
    }
    if (t.shadow.modal) {
      tokens.push({
        ...base,
        id: `${themeId}-1.11-shadow-modal`,
        category: '1.11',
        name: `${themeName} Modal Shadow`,
        shadowValue: t.shadow.modal,
        shadowLabel: 'modal',
      });
    }
    if (t.shadow.dropdown) {
      tokens.push({
        ...base,
        id: `${themeId}-1.11-shadow-dropdown`,
        category: '1.11',
        name: `${themeName} Dropdown Shadow`,
        shadowValue: t.shadow.dropdown,
        shadowLabel: 'dropdown',
      });
    }

    // 1.12 State Colors
    const stateMap: Array<[
      string,
      'primary' | 'success' | 'warning' | 'error' | 'info',
      'active' | 'light' | 'clarity'
    ]> = [
      ['primary-active',   'primary', 'active'],
      ['primary-light',    'primary', 'light'],
      ['primary-clarity',  'primary', 'clarity'],
      ['success-active',   'success', 'active'],
      ['success-light',    'success', 'light'],
      ['success-clarity',  'success', 'clarity'],
      ['warning-active',   'warning', 'active'],
      ['warning-light',    'warning', 'light'],
      ['warning-clarity',  'warning', 'clarity'],
      ['danger-active',    'error',   'active'],
      ['danger-light',     'error',   'light'],
      ['danger-clarity',   'error',   'clarity'],
      ['info-active',      'info',    'active'],
      ['info-light',       'info',    'light'],
      ['info-clarity',     'info',    'clarity'],
    ];
    for (const [key, stateColor, stateVariant] of stateMap) {
      const hex = (t.colors as Record<string, string | undefined>)[key];
      if (hex) {
        tokens.push({
          ...base,
          id: `${themeId}-1.12-${key}`,
          category: '1.12',
          name: `${themeName} ${key.replace('-', ' ')}`,
          hex,
          onColor: stateVariant === 'light' || stateVariant === 'clarity' ? hex : '#FFFFFF',
          stateColor,
          stateVariant,
        });
      }
    }

    // 1.13 Typography — font weight + line height from body metrics
    if (t.typography.bodyWeight) {
      tokens.push({
        ...base,
        id: `${themeId}-1.13-fw`,
        category: '1.13',
        name: `${themeName} Body Weight`,
        fontWeight: t.typography.bodyWeight,
        typographyLabel: 'Body text',
      });
    }
    if (t.typography.bodyLineHeight) {
      tokens.push({
        ...base,
        id: `${themeId}-1.13-lh`,
        category: '1.13',
        name: `${themeName} Line Height`,
        leading: t.typography.bodyLineHeight,
        typographyLabel: 'Body line height',
      });
    }

    // 1.14 Layout Dimensions
    if (t.layout.sidebarWidth) {
      tokens.push({
        ...base,
        id: `${themeId}-1.14-sidebar`,
        category: '1.14',
        name: `${themeName} Sidebar`,
        layoutValue: t.layout.sidebarWidth,
        layoutLabel: 'Sidebar expanded',
        layoutCssVar: '--mee-layout-sidebar-width',
      });
    }
    if (t.layout.sidebarCollapsedWidth) {
      tokens.push({
        ...base,
        id: `${themeId}-1.14-sidebar-collapsed`,
        category: '1.14',
        name: `${themeName} Sidebar Collapsed`,
        layoutValue: t.layout.sidebarCollapsedWidth,
        layoutLabel: 'Sidebar collapsed',
        layoutCssVar: '--mee-layout-sidebar-collapsed',
      });
    }
    if (t.layout.headerHeight) {
      tokens.push({
        ...base,
        id: `${themeId}-1.14-header`,
        category: '1.14',
        name: `${themeName} Header Height`,
        layoutValue: t.layout.headerHeight,
        layoutLabel: 'Top navbar',
        layoutCssVar: '--mee-layout-header-height',
      });
    }

    // Append to active tokens — skip duplicates by explicit id
    const existing = new Set(this._tokens().map(tok => tok.id));
    const fresh = tokens.filter(tok => !existing.has(tok.id));
    if (fresh.length > 0) {
      // Bypass addActive() to preserve explicit token IDs (addActive generates new IDs)
      this._tokens.update(curr => [...curr, ...fresh]);
    }

    this.loadedThemeIds.update(ids => [...ids, themeId]);
  }

  // ── Fetch-based scraping ─────────────────────────────────────────────────

  /** Fetch URL via CORS proxy and return raw candidates. Does NOT modify service state. */
  async scrapeUrl(rawUrl: string): Promise<ScrapeCandidate[]> {
    const url = rawUrl.startsWith('http') ? rawUrl : `https://${rawUrl}`;
    const proxy = `https://api.allorigins.win/get?url=${encodeURIComponent(url)}`;
    const res = await fetch(proxy, { signal: AbortSignal.timeout(20_000) });
    if (!res.ok) throw new Error(`Proxy HTTP ${res.status}`);
    const payload = await res.json() as { contents: string; status: { http_code: number } };
    if (!payload.contents) throw new Error('Proxy returned empty content — site may block scrapers');
    return this.extract(payload.contents, url);
  }

  private extract(html: string, sourceUrl: string): ScrapeCandidate[] {
    const results: ScrapeCandidate[] = [];
    let domain = sourceUrl;
    try { domain = new URL(sourceUrl).hostname.replace(/^www\./, ''); } catch { /* keep raw */ }
    const brand = domain.split('.')[0];

    // ── 1. meta theme-color ────────────────────────────────────────────────
    const themeRe = /<meta[^>]+(?:name=["']theme-color["'][^>]+content|content=["'][^"']+["'][^>]+name=["']theme-color["'])[^>]*>/i;
    const themeTag = html.match(themeRe)?.[0] ?? '';
    const themeHex = themeTag.match(/content=["'](#[0-9a-fA-F]{6})["']/i)?.[1]?.toUpperCase();
    if (themeHex) {
      results.push({ category: '1.1', name: `${brand} — theme-color`, source: 'scraped', sourceUrl, hex: themeHex, onColor: this.contrast(themeHex) });
    }

    // ── 2. CSS vars — primary/brand ────────────────────────────────────────
    const primaryVarRe = /--[\w-]*(?:primary|brand|cta|main|key|action)[\w-]*\s*:\s*(#[0-9a-fA-F]{6})\b/gi;
    const seenHex = new Set<string>(themeHex ? [themeHex] : []);
    for (const m of [...html.matchAll(primaryVarRe)]) {
      const hex = m[1].toUpperCase();
      if (seenHex.has(hex)) continue;
      seenHex.add(hex);
      const varName = m[0].split(':')[0].trim();
      results.push({ category: '1.1', name: `${brand} — ${varName}`, source: 'scraped', sourceUrl, hex, onColor: this.contrast(hex) });
    }

    // ── 3. CSS vars — secondary/accent ────────────────────────────────────
    const secVarRe = /--[\w-]*(?:secondary|accent|support|highlight)[\w-]*\s*:\s*(#[0-9a-fA-F]{6})\b/gi;
    for (const m of [...html.matchAll(secVarRe)]) {
      const hex = m[1].toUpperCase();
      if (seenHex.has(hex)) continue;
      seenHex.add(hex);
      const varName = m[0].split(':')[0].trim();
      results.push({ category: '1.2', name: `${brand} — ${varName}`, source: 'scraped', sourceUrl, hex, onColor: this.contrast(hex) });
    }

    // ── 4. CSS vars — surface/bg ───────────────────────────────────────────
    const surfVarRe = /--[\w-]*(?:surface|background|bg|neutral|canvas|base)[\w-]*\s*:\s*(#[0-9a-fA-F]{6})\b/gi;
    const seenSurf = new Set<string>();
    for (const m of [...html.matchAll(surfVarRe)]) {
      const hex = m[1].toUpperCase();
      if (seenSurf.has(hex) || this.luminance(hex) < 0.6) continue;
      seenSurf.add(hex);
      const varName = m[0].split(':')[0].trim();
      results.push({
        category: '1.3',
        name: `${brand} — ${varName}`,
        source: 'scraped', sourceUrl,
        bg: hex, surface: '#FFFFFF', surfaceVar: this.lighten(hex, -0.04), border: this.lighten(hex, -0.12),
        textColor: '#111827', textMid: '#6B7280',
        stops: [hex, '#FFFFFF', this.lighten(hex, -0.08), '#6B7280', '#111827'],
      });
    }

    // ── 5. Google Fonts ────────────────────────────────────────────────────
    const fontRe = /fonts\.googleapis\.com\/css[^"'<>]*[?&]family=([A-Za-z0-9+%:;|@,!.\s]+)/gi;
    const seenFont = new Set<string>();
    for (const m of [...html.matchAll(fontRe)]) {
      const raw = decodeURIComponent(m[1]);
      const families = raw.split(/[|&]/).map(f =>
        f.split(/[:@]/)[0].replace(/\+/g, ' ').trim()
      );
      for (const font of families) {
        if (!font || font.length < 2 || seenFont.has(font)) continue;
        seenFont.add(font);
        results.push({
          category: '1.4', name: font, source: 'scraped', sourceUrl,
          cssFamily: `'${font}', system-ui, sans-serif`,
          indicType: /noto/i.test(font) ? 'native' : 'pair',
        });
      }
    }

    // ── 6. Icon library detection ──────────────────────────────────────────
    const iconSigs = [
      { re: /material-symbols/i,  name: 'Material Symbols', cssClass: 'ms-outlined', iconType: 'material' as const, dep: 'Google Fonts CDN',       sw: 2 },
      { re: /material-icons/i,    name: 'Material Icons',   cssClass: 'ms-outlined', iconType: 'material' as const, dep: 'Google Fonts CDN',       sw: 2 },
      { re: /phosphor-icons|@phosphor/i, name: 'Phosphor',  cssClass: '',            iconType: 'svg'     as const, dep: 'NPM · 6 weights',         sw: 1.5 },
      { re: /lucide/i,            name: 'Lucide',            cssClass: '',            iconType: 'svg'     as const, dep: 'NPM · 1 weight',          sw: 2 },
      { re: /tabler-icons|@tabler/i, name: 'Tabler',         cssClass: '',            iconType: 'svg'     as const, dep: 'NPM · outlined + filled', sw: 1.5 },
      { re: /heroicons/i,         name: 'Heroicons',         cssClass: '',            iconType: 'svg'     as const, dep: 'NPM · 24/20px sizes',     sw: 2 },
      { re: /feather/i,           name: 'Feather',           cssClass: '',            iconType: 'svg'     as const, dep: 'NPM · minimal set',       sw: 2 },
    ];
    for (const sig of iconSigs) {
      if (sig.re.test(html)) {
        results.push({ category: '1.5', name: `${sig.name} (${domain})`, source: 'scraped', sourceUrl, cssClass: sig.cssClass, iconType: sig.iconType, dep: sig.dep, strokeWidth: sig.sw });
      }
    }

    // ── 7. CSS animation / motion tokens ──────────────────────────────────
    const durationRe = /(?:transition|animation)[^;{}]*?(\d+(?:\.\d+)?)(ms|s)\b/gi;
    const easingRe   = /cubic-bezier\([^)]+\)/g;
    const seenMotion = new Set<string>();
    const durations  = new Set<string>();
    const easings    = new Set<string>();

    for (const m of [...html.matchAll(durationRe)]) {
      const ms = m[2] === 's' ? `${parseFloat(m[1]) * 1000}ms` : `${m[1]}ms`;
      if (['0ms', '1ms'].includes(ms)) continue;
      durations.add(ms);
    }
    for (const m of [...html.matchAll(easingRe)]) {
      easings.add(m[0]);
    }

    // Pair most common duration with most relevant easing
    const easing = [...easings][0] ?? 'cubic-bezier(0.4, 0, 0.2, 1)';
    for (const dur of [...durations].slice(0, 3)) {
      const key = `${dur}::${easing}`;
      if (seenMotion.has(key)) continue;
      seenMotion.add(key);
      results.push({
        category: '1.6',
        name: `${brand} ${dur}`,
        source: 'scraped', sourceUrl,
        duration: dur, easing,
        motionLabel: `From ${domain}`,
      });
    }

    // ── 8. Radius tokens from CSS vars ────────────────────────────────────
    const radiusRe = /--[\w-]*radius[\w-]*:\s*([^;]+);/gi;
    const seenRadius = new Set<string>();
    for (const m of [...html.matchAll(radiusRe)]) {
      const val = m[1].trim();
      if (!val || seenRadius.has(val)) continue;
      seenRadius.add(val);
      const varName = m[0].split(':')[0].trim();
      results.push({
        category: '1.10',
        name: `${brand} — ${varName}`,
        source: 'scraped', sourceUrl,
        radiusValue: val,
        motionLabel: `From ${domain}`,
      });
      if (seenRadius.size >= 5) break; // cap to avoid noise
    }

    // ── 9. Shadow tokens from CSS vars ────────────────────────────────────
    const shadowRe = /--[\w-]*shadow[\w-]*:\s*([^;}{]+);/gi;
    const seenShadow = new Set<string>();
    for (const m of [...html.matchAll(shadowRe)]) {
      const val = m[1].trim();
      if (!val || val === 'none' || seenShadow.has(val)) continue;
      seenShadow.add(val);
      const varName = m[0].split(':')[0].trim();
      results.push({
        category: '1.11',
        name: `${brand} — ${varName}`,
        source: 'scraped', sourceUrl,
        shadowValue: val,
        shadowLabel: `From ${domain}`,
      });
      if (seenShadow.size >= 5) break; // cap to avoid noise
    }

    return results;
  }

  // ── Color utilities ───────────────────────────────────────────────────────

  private luminance(hex: string): number {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    const f = (c: number) => c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  }

  private contrast(hex: string): string {
    return this.luminance(hex) > 0.4 ? '#000000' : '#FFFFFF';
  }

  private lighten(hex: string, amount: number): string {
    const r = Math.min(255, Math.max(0, Math.round(parseInt(hex.slice(1, 3), 16) + amount * 255)));
    const g = Math.min(255, Math.max(0, Math.round(parseInt(hex.slice(3, 5), 16) + amount * 255)));
    const b = Math.min(255, Math.max(0, Math.round(parseInt(hex.slice(5, 7), 16) + amount * 255)));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase();
  }

  private hydrate(): DesignToken[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as DesignToken[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          // Merge: append any seed tokens that are missing from the stored snapshot
          // (handles new seed tokens added in code updates without wiping user data)
          const storedIds = new Set(parsed.map(t => t.id));
          const missing   = SEED.filter(s => !storedIds.has(s.id));
          return missing.length > 0 ? [...parsed, ...missing] : parsed;
        }
      }
    } catch { /* ignore */ }
    return [...SEED];
  }
}
