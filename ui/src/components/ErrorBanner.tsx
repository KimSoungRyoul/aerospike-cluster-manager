"use client"

import { Button } from "@/components/Button"

export interface ErrorBannerProps {
  message: string
  onRetry?: () => void
  disabled?: boolean
  /** True when previously loaded data is still rendered underneath the banner. */
  staleData?: boolean
}

export function ErrorBanner({
  message,
  onRetry,
  disabled,
  staleData,
}: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
    >
      <div className="flex flex-col gap-0.5">
        <span>{message}</span>
        {staleData && (
          <span className="text-[11px] text-red-600/80 dark:text-red-400/80">
            Showing data from the last successful load.
          </span>
        )}
      </div>
      {onRetry && (
        <Button
          variant="secondary"
          className="h-7 px-2 text-xs"
          onClick={onRetry}
          disabled={disabled}
        >
          Retry
        </Button>
      )}
    </div>
  )
}
