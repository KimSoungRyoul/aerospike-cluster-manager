"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Lazily-loaded CodeEditor – use this instead of importing CodeEditor directly
 * to keep Monaco out of the initial bundle for a given route.
 */
export const LazyCodeEditor = dynamic(
  () => import("@/components/common/code-editor").then((m) => m.CodeEditor),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[300px] w-full rounded-md" />,
  },
);
