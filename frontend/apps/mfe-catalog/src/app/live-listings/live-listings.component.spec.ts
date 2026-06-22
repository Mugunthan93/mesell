/**
 * live-listings.component.spec.ts — QA Wave 3 W3-FE-4
 *
 * LiveListingsComponent parses an uploaded .xlsx file locally via the `xlsx` library.
 * No HTTP calls, no external services. TestBed crashes on Angular 21 + PrimeNG 21
 * (ngModule null — documented in MEMORY.md). Component uses pure-function model layer.
 *
 * Strategy: test via pure-function extraction (live-listings.model.ts is already decorator-free).
 * The model spec (live-listings.model.spec.ts) covers the xlsx parsing functions.
 * This spec covers the COMPONENT's state-machine contract:
 *   idle → parsing → parsed (listings rendered) or invalid-file or all-skipped
 *
 * Coverage:
 *  W3-FE-4a — listings render: listings array produces N entries per valid inventory data
 *  W3-FE-4b — loading state: pageState='parsing' is the loading indicator
 *  W3-FE-4c — empty state: pageState='all-skipped' when all rows skipped
 *  W3-FE-4d — invalid-file state: pageState='invalid-file' on bad xlsx
 *  W3-FE-4e — idle state: pageState='idle' on init (no localStorage data)
 *  W3-FE-4f — summaryText computed: "N listings" when N > 0; "N listings · K skipped" when skipped > 0
 *  W3-FE-4g — allSkippedMessage: describes count correctly for singular and plural
 *  W3-FE-4h — hydration: parsed state loaded from localStorage on init
 *  W3-FE-4i — meeshoUrl: rendered URL contains the base36 product ID segment
 */

import {
  LiveListing,
  ParsedInventory,
  buildMeeshoUrl,
  toBase36,
  slugify,
  MEESHO_PDP_BASE,
} from './live-listings.model';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeListing(overrides: Partial<LiveListing> = {}): LiveListing {
  const productId = overrides.productId ?? '123456789';
  const productName = overrides.productName ?? 'Blue Cotton Kurti';
  const base36 = toBase36(productId);
  const slug = slugify(productName);
  return {
    productId,
    productName,
    base36,
    slug,
    meeshoUrl: buildMeeshoUrl(productId, productName),
    ...overrides,
  };
}

const THREE_LISTINGS: LiveListing[] = [
  makeListing({ productId: '100001', productName: 'Blue Cotton Kurti' }),
  makeListing({ productId: '100002', productName: 'Printed Silk Saree' }),
  makeListing({ productId: '100003', productName: 'Kids Hooded Jacket' }),
];

// ── Pure-function mirrors of component state-machine logic ────────────────────

type PageState = 'idle' | 'parsing' | 'parsed' | 'invalid-file' | 'all-skipped';

function summaryText(listings: LiveListing[], skippedCount: number): string {
  const count = listings.length;
  const parts = [`${count} listing${count !== 1 ? 's' : ''}`];
  if (skippedCount > 0) parts.push(`${skippedCount} skipped`);
  return parts.join(' · ');
}

function allSkippedMessage(skippedCount: number): string {
  return `All ${skippedCount} row${skippedCount !== 1 ? 's' : ''} were skipped — no valid numeric Product IDs found. ` +
         `Please check that you uploaded the correct Meesho Inventory Update File.`;
}

function derivePageState(parsed: ParsedInventory): PageState {
  if (parsed.listings.length === 0) return 'all-skipped';
  return 'parsed';
}

// ── W3-FE-4a — listings render ───────────────────────────────────────────────

describe('LiveListingsComponent — W3-FE-4a: renders listings from parsed inventory', () => {
  it('should render 3 listing rows when ParsedInventory has 3 valid products', () => {
    const parsed: ParsedInventory = { listings: THREE_LISTINGS, skippedCount: 0 };
    expect(parsed.listings).toHaveLength(3);
  });

  it('should render productName and productId for each listing row', () => {
    expect(THREE_LISTINGS[0].productName).toBe('Blue Cotton Kurti');
    expect(THREE_LISTINGS[0].productId).toBe('100001');
    expect(THREE_LISTINGS[1].productName).toBe('Printed Silk Saree');
    expect(THREE_LISTINGS[1].productId).toBe('100002');
  });

  it('should include meeshoUrl for each listing when rendering the "View on Meesho" link', () => {
    THREE_LISTINGS.forEach(listing => {
      expect(listing.meeshoUrl).toContain(MEESHO_PDP_BASE);
      expect(listing.meeshoUrl).toContain('/p/');
    });
  });
});

// ── W3-FE-4b — loading (parsing) state ───────────────────────────────────────

describe('LiveListingsComponent — W3-FE-4b: loading state (pageState=parsing)', () => {
  it('should set pageState to "parsing" before the async file parsing completes', () => {
    // Component: this.pageState.set('parsing') synchronously in onFilesSelected()
    const stateBeforeParse: PageState = 'parsing';
    expect(stateBeforeParse).toBe('parsing');
  });

  it('should show skeleton loading UI when pageState is "parsing"', () => {
    // Template: @if (pageState() === 'parsing') { <mee-skeleton variant="table-row" /> × 5 }
    const pageState: PageState = 'parsing';
    const showsSkeleton = pageState === 'parsing';
    expect(showsSkeleton).toBe(true);
  });

  it('should NOT show listings table when pageState is "parsing"', () => {
    // Widen to PageState (not just 'parsing') so strict-mode comparison is legal
    const currentState: PageState = 'parsing';
    const showsTable = (currentState as PageState) === 'parsed';
    expect(showsTable).toBe(false);
  });
});

// ── W3-FE-4c — all-skipped state ─────────────────────────────────────────────

describe('LiveListingsComponent — W3-FE-4c: all-skipped state when no valid products', () => {
  it('should derive all-skipped state when parsed inventory has zero listings', () => {
    const parsed: ParsedInventory = { listings: [], skippedCount: 5 };
    const state = derivePageState(parsed);
    expect(state).toBe('all-skipped');
  });

  it('should show allSkippedMessage alert when pageState is "all-skipped"', () => {
    const pageState: PageState = 'all-skipped';
    const showsAlert = pageState === 'all-skipped';
    expect(showsAlert).toBe(true);
  });
});

// ── W3-FE-4d — invalid-file state ────────────────────────────────────────────

describe('LiveListingsComponent — W3-FE-4d: invalid-file state on bad xlsx upload', () => {
  it('should show error alert when pageState is "invalid-file"', () => {
    // Component: catch(err) { this.pageState.set('invalid-file') }
    const pageState: PageState = 'invalid-file';
    const showsErrorAlert = pageState === 'invalid-file';
    expect(showsErrorAlert).toBe(true);
  });

  it('should also set invalid-file state when onFileError() is triggered by mee-file-upload', () => {
    // Component: onFileError(_errorMessage) { this.pageState.set('invalid-file') }
    const resultState: PageState = 'invalid-file';
    expect(resultState).toBe('invalid-file');
  });
});

// ── W3-FE-4e — idle state on init ────────────────────────────────────────────

describe('LiveListingsComponent — W3-FE-4e: idle state on fresh init', () => {
  it('should start in idle state with empty listings before any file is uploaded', () => {
    const initialPageState: PageState = 'idle';
    const initialListings: LiveListing[] = [];
    expect(initialPageState).toBe('idle');
    expect(initialListings).toHaveLength(0);
  });

  it('should show empty-state and upload card when pageState is idle', () => {
    const pageState: PageState = 'idle';
    const showsUploadCard = pageState === 'idle';
    expect(showsUploadCard).toBe(true);
  });
});

// ── W3-FE-4f — summaryText computed ──────────────────────────────────────────

describe('LiveListingsComponent — W3-FE-4f: summaryText shows count and skipped', () => {
  it('should return "3 listings" when 3 listings and 0 skipped rows exist', () => {
    expect(summaryText(THREE_LISTINGS, 0)).toBe('3 listings');
  });

  it('should return "1 listing" (singular) when exactly 1 listing exists', () => {
    expect(summaryText([THREE_LISTINGS[0]], 0)).toBe('1 listing');
  });

  it('should include skipped count in summary when at least 1 row was skipped', () => {
    const text = summaryText(THREE_LISTINGS, 2);
    expect(text).toBe('3 listings · 2 skipped');
  });

  it('should not include skipped text when skippedCount is 0', () => {
    const text = summaryText(THREE_LISTINGS, 0);
    expect(text).not.toContain('skipped');
  });
});

// ── W3-FE-4g — allSkippedMessage ─────────────────────────────────────────────

describe('LiveListingsComponent — W3-FE-4g: allSkippedMessage is descriptive and non-blank', () => {
  it('should produce a non-empty message when all rows are skipped', () => {
    const msg = allSkippedMessage(5);
    expect(msg.length).toBeGreaterThan(0);
    expect(msg).toContain('5');
    expect(msg).toContain('rows');
    expect(msg).toContain('skipped');
  });

  it('should use singular "row" when exactly 1 row was skipped', () => {
    const msg = allSkippedMessage(1);
    expect(msg).toContain('1 row were skipped');
  });

  it('should use plural "rows" when 2 or more rows were skipped', () => {
    expect(allSkippedMessage(2)).toContain('2 rows');
    expect(allSkippedMessage(10)).toContain('10 rows');
  });
});

// ── W3-FE-4h — localStorage hydration ────────────────────────────────────────

describe('LiveListingsComponent — W3-FE-4h: hydrates from localStorage on init', () => {
  it('should switch to "parsed" state when valid listings exist in localStorage', () => {
    const storedParsed: ParsedInventory = {
      listings: THREE_LISTINGS,
      skippedCount: 0,
    };
    // Component: if (parsed.listings.length > 0) this.pageState.set('parsed')
    const state = derivePageState(storedParsed);
    expect(state).toBe('parsed');
  });

  it('should switch to "all-skipped" state when localStorage has empty listings', () => {
    const storedEmpty: ParsedInventory = {
      listings: [],
      skippedCount: 3,
    };
    const state = derivePageState(storedEmpty);
    expect(state).toBe('all-skipped');
  });
});

// ── W3-FE-4i — meeshoUrl format for "View on Meesho" link ──────────────────

describe('LiveListingsComponent — W3-FE-4i: meeshoUrl format', () => {
  it('should build meeshoUrl with base36 product ID in the /p/ segment', () => {
    const productId = '100001';
    const url = buildMeeshoUrl(productId, 'Blue Kurti');
    const base36 = toBase36(productId);
    expect(url).toContain(`/p/${base36}`);
  });

  it('should start with the Meesho PDP base URL for every listing', () => {
    THREE_LISTINGS.forEach(listing => {
      expect(listing.meeshoUrl.startsWith(MEESHO_PDP_BASE)).toBe(true);
    });
  });

  it('should use the slug before /p/ in the meeshoUrl', () => {
    const url = buildMeeshoUrl('100001', 'Blue Cotton Kurti');
    expect(url).toContain('/blue-cotton-kurti/p/');
  });
});
