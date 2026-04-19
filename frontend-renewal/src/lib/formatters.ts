/**
 * Number / byte / duration / TTL / relative-time formatters.
 *
 * Ported from `frontend/src/lib/formatters.ts` — no style dependencies.
 */

export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`
  return num.toString()
}

export function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`
  if (ms < 1000) return `${ms.toFixed(1)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export function formatPercent(value: number, total: number): number {
  if (total === 0) return 0
  return Math.round((value / total) * 100)
}

export const NEVER_EXPIRE_TTL = 4294967295 // 0xFFFFFFFF — Aerospike "never expires" sentinel

/**
 * Convert TTL (seconds remaining) to an expiration datetime.
 * Used in table views to show when a record expires.
 *
 * Returns a short form ("yyyy-mm-dd hh:mm", 16 chars) suited for a narrow
 * column. Use ``includeSeconds=true`` for the long form ("yyyy-mm-dd hh:mm:ss",
 * 19 chars) when displaying in a wider context (detail panels, tooltips).
 */
export function formatTTLAsExpiry(ttl: number, includeSeconds = false): string {
  if (ttl === -1 || ttl === NEVER_EXPIRE_TTL) return "Never"
  if (ttl === 0) return "Default"

  const expiry = new Date(Date.now() + ttl * 1000)
  const y = expiry.getFullYear()
  const mo = String(expiry.getMonth() + 1).padStart(2, "0")
  const d = String(expiry.getDate()).padStart(2, "0")
  const h = String(expiry.getHours()).padStart(2, "0")
  const mi = String(expiry.getMinutes()).padStart(2, "0")
  if (!includeSeconds) {
    return `${y}-${mo}-${d} ${h}:${mi}`
  }
  const s = String(expiry.getSeconds()).padStart(2, "0")
  return `${y}-${mo}-${d} ${h}:${mi}:${s}`
}

export function formatTTLHuman(ttl: number): string {
  if (ttl === -1 || ttl === NEVER_EXPIRE_TTL) return "Never expires"
  if (ttl === 0) return "Default namespace TTL"
  return formatUptime(ttl)
}

export function truncateMiddle(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  const half = Math.floor((maxLen - 3) / 2)
  return `${str.slice(0, half)}...${str.slice(-half)}`
}

/**
 * Format an ISO-8601 date string as a human-readable relative time.
 *
 * Handles `null`/`undefined` gracefully (returns "N/A") and falls back to the
 * raw string when the date cannot be parsed.
 */
export function formatRelativeTime(
  isoString: string | null | undefined,
): string {
  if (!isoString) return "N/A"
  try {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    if (diffMs < 0) return "just now"
    const diffSec = Math.floor(diffMs / 1000)
    if (diffSec < 60) return `${diffSec}s ago`
    const diffMin = Math.floor(diffSec / 60)
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHr = Math.floor(diffMin / 60)
    if (diffHr < 24) return `${diffHr}h ago`
    const diffDay = Math.floor(diffHr / 24)
    return `${diffDay}d ago`
  } catch {
    return isoString
  }
}
