"use client";

import { Button } from "@/components/ui/button";

export default function K8sError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 p-6">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="text-base-content/60 text-sm">
        {error.message || "An unexpected error occurred in the K8s management area."}
      </p>
      <Button onClick={reset} variant="outline">
        Try again
      </Button>
    </div>
  );
}
