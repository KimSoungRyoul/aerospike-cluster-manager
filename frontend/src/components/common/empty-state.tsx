"use client";

import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "animate-fade-in flex flex-col items-center justify-center py-16 text-center",
        className,
      )}
    >
      {Icon && (
        <div className="relative mb-5">
          <div className="bg-accent/10 absolute inset-0 scale-150 rounded-2xl blur-xl" />
          <div className="bg-base-200/80 dark:bg-base-200/50 relative rounded-2xl p-4 backdrop-blur-lg backdrop-saturate-[1.3]">
            <Icon className="text-muted-foreground h-7 w-7" />
          </div>
        </div>
      )}
      <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
      {description && (
        <p className="text-muted-foreground mt-1.5 max-w-sm text-sm leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
