import * as React from "react";

import { cn } from "@/lib/utils";

interface ProgressProps extends React.HTMLAttributes<HTMLProgressElement> {
  value?: number;
  max?: number;
}

const Progress = React.forwardRef<HTMLProgressElement, ProgressProps>(
  ({ className, value = 0, max = 100, ...props }, ref) => (
    <progress
      ref={ref}
      className={cn("progress progress-primary w-full", className)}
      value={value}
      max={max}
      {...props}
    />
  ),
);
Progress.displayName = "Progress";

export { Progress };
