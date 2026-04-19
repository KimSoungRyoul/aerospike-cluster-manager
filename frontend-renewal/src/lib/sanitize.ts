/**
 * Strip control characters and trim whitespace from user input.
 */
export function sanitizeInput(input: string): string {
  // Remove control characters (except common whitespace)
  return input.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "").trim()
}

/**
 * Validate and sanitize a hostname.
 * Allows alphanumeric, dots, hyphens, colons (IPv6), and square brackets.
 */
export function sanitizeHostname(hostname: string): string {
  const trimmed = hostname.trim()
  if (!/^[\w.:\-[\]]+$/.test(trimmed)) {
    return ""
  }
  return trimmed
}

/**
 * Sanitize a filename by removing path traversal characters and unsafe chars.
 */
export function sanitizeFilename(filename: string): string {
  return filename
    .replace(/\.\./g, "")
    .replace(/[/\\:*?"<>|]/g, "")
    .trim()
}
