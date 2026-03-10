import * as React from "react";

import { cn } from "@/lib/utils";

const Select = React.forwardRef<HTMLSelectElement, React.ComponentProps<"select">>(
  ({ className, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn("select select-bordered w-full text-base sm:text-sm", className)}
        {...props}
      >
        {children}
      </select>
    );
  },
);
Select.displayName = "Select";

const SelectNative = Select;

export { Select, SelectNative };
