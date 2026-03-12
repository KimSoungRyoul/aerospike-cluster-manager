"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SwitchProps extends Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "onChange" | "type"
> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, checked = false, onCheckedChange, disabled, ...props }, ref) => (
    <input
      type="checkbox"
      ref={ref}
      role="switch"
      className={cn("toggle toggle-primary", className)}
      checked={checked}
      disabled={disabled}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
      {...props}
    />
  ),
);
Switch.displayName = "Switch";

export { Switch };
