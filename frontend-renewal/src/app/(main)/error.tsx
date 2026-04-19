"use client"

import { useEffect } from "react"

import { FullPageError } from "@/components/common/FullPageError"

export default function MainError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[MainError]", error)
  }, [error])

  return (
    <FullPageError
      title="Could not load this page"
      message={
        error.message ||
        "An unexpected error occurred while rendering this section. Try again, or return to the cluster list."
      }
      onRetry={reset}
      retryLabel="Try again"
    />
  )
}
