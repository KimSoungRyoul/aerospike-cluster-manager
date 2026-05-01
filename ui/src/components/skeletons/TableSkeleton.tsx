import { TableCell, TableRow } from "@/components/Table"

// Restrict cellWidth to a literal union so callers cannot pass an arbitrary
// Tailwind-class string (e.g. "w-[173px]" or a dynamically built name).
// Tailwind's JIT compiler purges any class it cannot statically see in
// source. A dynamic string would compile fine but get stripped at build
// time, collapsing the skeleton bar to width:auto. Each value below is
// referenced statically in this file so the JIT keeps it.
export type SkeletonCellWidth =
  | "w-12"
  | "w-16"
  | "w-20"
  | "w-24"
  | "w-28"
  | "w-32"
  | "w-40"
  | "w-full"

// TableSkeleton renders pulse-shimmer placeholder rows that mirror the shape
// of the table while the initial fetch is in flight. Use this inside a
// <TableBody> when `loading && !data` so users see structure instead of an
// empty card.
//
// Accessibility: the first cell of the first row contains a visually-hidden
// "Loading…" status node with role="status" + aria-live="polite" so screen
// readers announce the loading state instead of nothing while a request is
// in flight.
export function TableSkeleton({
  rows = 5,
  cols,
  cellWidth = "w-20",
}: {
  rows?: number
  cols: number
  // Tailwind width class for the inner skeleton bar. Tweak per page if needed.
  cellWidth?: SkeletonCellWidth
}) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <TableRow key={r}>
          {Array.from({ length: cols }).map((_, c) => (
            <TableCell key={c}>
              {r === 0 && c === 0 && (
                <span
                  role="status"
                  aria-live="polite"
                  aria-hidden="false"
                  className="sr-only"
                >
                  Loading…
                </span>
              )}
              <div
                className={`h-3 ${cellWidth} animate-pulse rounded bg-gray-200 dark:bg-gray-800`}
              />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}
