"use client"

import { useEffect } from "react"

import { FullPageError } from "@/components/common/FullPageError"

export default function ClusterError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[ClusterError]", error)
  }, [error])

  return (
    <FullPageError
      title="Could not load this cluster"
      message={
        error.message ||
        "The cluster could not be loaded. It may be unreachable or temporarily unavailable."
      }
      onRetry={reset}
      retryLabel="Retry"
    />
  )
}
