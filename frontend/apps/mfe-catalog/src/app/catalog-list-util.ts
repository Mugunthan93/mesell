/**
 * catalog-list-util.ts — pure utility functions for CatalogListComponent.
 *
 * No Angular dependencies — functions can be tested without TestBed.
 */

/**
 * formatRelativeTime — converts an ISO-8601 timestamp to a relative time string.
 *
 * Examples:
 *   "just now"        (< 1 minute ago)
 *   "2 minutes ago"   (< 1 hour ago)
 *   "3 hours ago"     (< 1 day ago)
 *   "2 days ago"      (< 30 days ago)
 *   "15 Oct 2024"     (≥ 30 days ago — absolute date)
 *
 * @param isoString - ISO-8601 date string (e.g. "2024-10-15T14:30:00Z")
 * @returns human-readable relative or absolute time string
 */
export function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHrs = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1)   return 'just now';
  if (diffMin < 60)  return `${diffMin} ${diffMin === 1 ? 'minute' : 'minutes'} ago`;
  if (diffHrs < 24)  return `${diffHrs} ${diffHrs === 1 ? 'hour' : 'hours'} ago`;
  if (diffDays < 30) return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;

  // Absolute date for older items
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}
