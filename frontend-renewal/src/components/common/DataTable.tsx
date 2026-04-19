"use client"

import {
  type ColumnDef,
  type OnChangeFn,
  type Row,
  type RowSelectionState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table"
import {
  RiArrowDownLine,
  RiArrowUpDownLine,
  RiArrowUpLine,
} from "@remixicon/react"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRoot,
  TableRow,
} from "@/components/Table"
import { EmptyState } from "@/components/common/EmptyState"
import { cx } from "@/lib/utils"

type Density = "compact" | "default" | "comfortable"

const densityPadding: Record<Density, { th: string; td: string }> = {
  compact: { th: "px-3 py-1.5", td: "px-3 py-1.5" },
  default: { th: "px-4 py-2.5", td: "px-4 py-3" },
  comfortable: { th: "px-4 py-3", td: "px-4 py-4" },
}

interface DataTableProps<TData, TValue> {
  data: TData[]
  columns: ColumnDef<TData, TValue>[]
  loading?: boolean
  emptyState?: React.ReactNode
  rowSelection?: RowSelectionState
  onRowSelectionChange?: OnChangeFn<RowSelectionState>
  onRowClick?: (row: Row<TData>) => void
  sorting?: SortingState
  onSortingChange?: OnChangeFn<SortingState>
  getRowId?: (row: TData) => string
  density?: Density
  className?: string
  tableMinWidth?: number
  testId?: string
  loadingRows?: number
}

/**
 * Minimal DataTable for Phase 0. Wraps `@tanstack/react-table` with renewal's
 * Tremor Table primitives. Does NOT yet support virtualization, column
 * pinning, or mobile card layout — Stream A will extend with those if needed.
 */
export function DataTable<TData, TValue>({
  data,
  columns,
  loading = false,
  emptyState,
  rowSelection,
  onRowSelectionChange,
  onRowClick,
  sorting,
  onSortingChange,
  getRowId,
  density = "default",
  className,
  tableMinWidth,
  testId = "data-table",
  loadingRows = 8,
}: DataTableProps<TData, TValue>) {
  const table = useReactTable({
    data,
    columns,
    state: {
      rowSelection: rowSelection ?? {},
      ...(sorting ? { sorting } : {}),
    },
    enableRowSelection: true,
    onRowSelectionChange,
    ...(onSortingChange ? { onSortingChange } : {}),
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
    ...(getRowId ? { getRowId } : {}),
  })

  const pad = densityPadding[density]
  const { rows } = table.getRowModel()

  if (loading && data.length === 0) {
    return (
      <div
        className={cx("relative min-w-0 flex-1", className)}
        data-testid={testId}
      >
        <TableRoot>
          <Table
            className={cx("table-fixed", !tableMinWidth && "w-full")}
            style={tableMinWidth ? { minWidth: tableMinWidth } : undefined}
          >
            <TableHead>
              <TableRow>
                {columns.map((_, i) => (
                  <TableHeaderCell key={i} className={pad.th}>
                    <div className="h-3 w-16 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
                  </TableHeaderCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {Array.from({ length: loadingRows }).map((_, rowIdx) => (
                <TableRow key={rowIdx}>
                  {columns.map((_, colIdx) => (
                    <TableCell key={colIdx} className={pad.td}>
                      <div
                        className={cx(
                          "h-3 animate-pulse rounded bg-gray-200 dark:bg-gray-800",
                          colIdx === 0 ? "w-3/4" : "w-1/2",
                        )}
                      />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableRoot>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div
        className={cx("relative min-w-0 flex-1", className)}
        data-testid={testId}
      >
        {emptyState ?? (
          <EmptyState
            title="No records"
            description="No data available to display"
          />
        )}
      </div>
    )
  }

  return (
    <div
      className={cx("relative min-w-0 flex-1", className)}
      data-testid={testId}
    >
      {loading && (
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 z-10 h-0.5 overflow-hidden"
        >
          <div className="h-full w-1/4 animate-pulse rounded-full bg-indigo-500" />
        </div>
      )}
      <TableRoot>
        <Table
          className={cx("table-fixed", !tableMinWidth && "w-full")}
          style={tableMinWidth ? { minWidth: tableMinWidth } : undefined}
        >
          <TableHead data-testid={`${testId}-head`}>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort =
                    Boolean(onSortingChange) && header.column.getCanSort()
                  const sorted = header.column.getIsSorted()
                  return (
                    <TableHeaderCell
                      key={header.id}
                      className={cx(
                        pad.th,
                        "text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400",
                        canSort && "cursor-pointer select-none",
                      )}
                      style={
                        header.column.columnDef.size
                          ? { width: header.column.columnDef.size }
                          : undefined
                      }
                      onClick={
                        canSort
                          ? header.column.getToggleSortingHandler()
                          : undefined
                      }
                    >
                      <div className="flex items-center gap-1.5">
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                        {canSort && (
                          <>
                            {sorted === "asc" && (
                              <RiArrowUpLine
                                className="size-3 shrink-0 text-indigo-500"
                                aria-hidden="true"
                              />
                            )}
                            {sorted === "desc" && (
                              <RiArrowDownLine
                                className="size-3 shrink-0 text-indigo-500"
                                aria-hidden="true"
                              />
                            )}
                            {!sorted && (
                              <RiArrowUpDownLine
                                className="size-3 shrink-0 text-gray-400 dark:text-gray-600"
                                aria-hidden="true"
                              />
                            )}
                          </>
                        )}
                      </div>
                    </TableHeaderCell>
                  )
                })}
              </TableRow>
            ))}
          </TableHead>
          <TableBody data-testid={`${testId}-body`}>
            {rows.map((row, idx) => (
              <TableRow
                key={row.id}
                className={cx(
                  onRowClick &&
                    "cursor-pointer transition hover:bg-gray-50 dark:hover:bg-gray-900/40",
                )}
                onClick={() => onRowClick?.(row)}
                onKeyDown={(e) => {
                  if (onRowClick && (e.key === "Enter" || e.key === " ")) {
                    e.preventDefault()
                    onRowClick(row)
                  }
                }}
                tabIndex={onRowClick ? 0 : undefined}
                data-testid={`${testId}-row-${idx}`}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    className={cx(
                      pad.td,
                      "overflow-hidden text-ellipsis whitespace-nowrap",
                    )}
                    style={
                      cell.column.columnDef.size
                        ? { width: cell.column.columnDef.size }
                        : undefined
                    }
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableRoot>
    </div>
  )
}
