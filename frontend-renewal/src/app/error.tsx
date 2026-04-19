"use client"

import { RiAlertLine } from "@remixicon/react"
import { useEffect } from "react"

import { Button } from "@/components/Button"

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[RootError]", error)
  }, [error])

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 p-10 text-center">
      <div className="rounded-lg bg-red-50 p-3 dark:bg-red-500/10">
        <RiAlertLine
          aria-hidden="true"
          className="size-7 text-red-600 dark:text-red-400"
        />
      </div>
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
          Something went wrong
        </h2>
        <p className="max-w-md text-sm text-gray-500 dark:text-gray-400">
          {error.message ||
            "An unexpected error occurred. Please try again or return to the home page."}
        </p>
      </div>
      <div className="flex gap-3">
        <Button
          variant="secondary"
          onClick={() => (window.location.href = "/")}
        >
          Go home
        </Button>
        <Button variant="primary" onClick={reset}>
          Try again
        </Button>
      </div>
    </div>
  )
}
