import type { ComponentType, ReactNode } from "react"

import { cx } from "@/lib/utils"

// Lenient icon type to accept both lucide-style (SVGProps) and remixicon-style icons.
type IconComponent = ComponentType<{
  className?: string
  "aria-hidden"?: boolean | "true" | "false"
}>

interface EmptyStateProps {
  icon?: IconComponent
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cx(
        "flex flex-col items-center justify-center rounded-md border border-dashed border-gray-200 px-6 py-12 text-center dark:border-gray-800",
        className,
      )}
    >
      {Icon && (
        <div className="mb-4 rounded-lg bg-gray-100 p-3 dark:bg-gray-900">
          <Icon
            aria-hidden="true"
            className="size-6 text-gray-500 dark:text-gray-400"
          />
        </div>
      )}
      <h3 className="text-base font-semibold text-gray-900 dark:text-gray-50">
        {title}
      </h3>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-gray-500 dark:text-gray-400">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
