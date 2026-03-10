import * as React from "react";

import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline";
}

const variantClasses: Record<string, string> = {
  default: "badge",
  secondary: "badge-ghost",
  destructive: "badge-error",
  outline: "badge-outline",
};

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn("badge text-xs font-medium", variantClasses[variant], className)}
      {...props}
    />
  );
}

export { Badge };
