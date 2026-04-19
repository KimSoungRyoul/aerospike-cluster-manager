"use client"

import { RiAlertLine, RiRefreshLine } from "@remixicon/react"
import type { ComponentType } from "react"

import { Button } from "@/components/Button"

type IconComponent = ComponentType<{
  className?: string
  "aria-hidden"?: boolean | "true" | "false"
}>

interface FullPageErrorProps {
  icon?: IconComponent
  title?: string
  message?: string
  onRetry?: () => void
  retryLabel?: string
}

export function FullPageError({
  icon: Icon = RiAlertLine,
  title = "Something went wrong",
  message,
  onRetry,
  retryLabel = "Retry",
}: FullPageErrorProps) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-10 text-center">
      <div className="rounded-lg bg-red-50 p-3 dark:bg-red-500/10">
        <Icon
          aria-hidden="true"
          className="size-6 text-red-600 dark:text-red-400"
        />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
          {title}
        </h3>
        {message && (
          <p className="max-w-md text-sm text-gray-500 dark:text-gray-400">
            {message}
          </p>
        )}
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          <RiRefreshLine className="mr-2 size-4" aria-hidden="true" />
          {retryLabel}
        </Button>
      )}
    </div>
  )
}
