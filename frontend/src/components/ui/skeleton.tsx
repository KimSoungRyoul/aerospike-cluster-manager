import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton h-4 w-full", className)} {...props} />;
}

export { Skeleton };
