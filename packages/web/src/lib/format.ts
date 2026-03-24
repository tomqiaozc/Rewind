import { formatDistanceToNow, format, parseISO } from "date-fns";

/**
 * Format a number with thousands separators.
 */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat().format(n);
}

/**
 * Format a large number compactly (e.g., 1.2K, 3.4M).
 */
export function formatCompact(n: number): string {
  if (n < 1000) return String(n);
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}K`;
  return `${(n / 1_000_000).toFixed(1)}M`;
}

/**
 * Format a token count (e.g., "1,234" or "1.2M").
 */
export function formatTokens(n: number): string {
  if (n >= 1_000_000) return formatCompact(n);
  return formatNumber(n);
}

/**
 * Format seconds as human-readable duration (e.g., "5m 30s", "2h 15m").
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds <= 0) return "--";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m < 60) return s > 0 ? `${m}m ${s}s` : `${m}m`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm > 0 ? `${h}h ${rm}m` : `${h}h`;
}

/**
 * Format an ISO datetime string as relative time (e.g., "5 minutes ago").
 */
export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "--";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return "--";
  }
}

/**
 * Format an ISO datetime string as a readable date.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "--";
  try {
    return format(parseISO(iso), "MMM d, yyyy");
  } catch {
    return "--";
  }
}

/**
 * Format an ISO datetime string as date + time.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "--";
  try {
    return format(parseISO(iso), "MMM d, yyyy h:mm a");
  } catch {
    return "--";
  }
}
