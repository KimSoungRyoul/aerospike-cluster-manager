"use client";

import { AlertTriangle } from "lucide-react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { LucideIcon } from "lucide-react";

interface FullPageErrorProps {
  icon?: LucideIcon;
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export function FullPageError({
  icon: Icon = AlertTriangle,
  title = "Something went wrong",
  message,
  onRetry,
  retryLabel = "Retry",
}: FullPageErrorProps) {
  return (
    <div className="animate-fade-in flex flex-col items-center justify-center p-12">
      <div className="relative mb-5">
        <div className="bg-error/10 absolute inset-0 scale-150 rounded-2xl blur-xl" />
        <div className="bg-base-200/80 relative rounded-2xl p-4">
          <Icon className="text-error h-7 w-7" />
        </div>
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      {message && <p className="text-muted-foreground mt-1 text-sm">{message}</p>}
      {onRetry && (
        <Button className="mt-5" onClick={onRetry}>
          <RefreshCw className="mr-2 h-4 w-4" />
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
