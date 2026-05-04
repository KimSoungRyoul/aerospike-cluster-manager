"use client"

import { ApiError } from "./client"

/**
 * Log a fetch failure with structured context.
 *
 * Goes through `console.error` so it shows up in DevTools and any
 * downstream telemetry that hooks into console output. Extracts
 * status/detail/body from `ApiError` to keep the payload terse;
 * passes the raw error through otherwise.
 */
export function logFetchError(scope: string, err: unknown): void {
  if (err instanceof ApiError) {
    // eslint-disable-next-line no-console
    console.error(`[${scope}] fetch failed`, {
      status: err.status,
      detail: err.detail,
      body: err.body,
    })
    return
  }
  // eslint-disable-next-line no-console
  console.error(`[${scope}] fetch failed`, err)
}
