"use client";

import React from "react";
import { Button } from "@/components/ui/button";

interface LoadingButtonProps extends React.ComponentProps<typeof Button> {
  loading?: boolean;
}

export const LoadingButton = React.forwardRef<HTMLButtonElement, LoadingButtonProps>(
  function LoadingButton({ loading, disabled, children, ...props }, ref) {
    return (
      <Button ref={ref} disabled={disabled || loading} {...props}>
        {loading && <span className="loading loading-spinner loading-xs mr-2" />}
        {children}
      </Button>
    );
  },
);
