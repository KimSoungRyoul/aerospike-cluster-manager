import React from "react"
import type { ComponentType } from "react"

import { Card } from "@/components/Card"
import { cx } from "@/lib/utils"

type IconComponent = ComponentType<{
  className?: string
  "aria-hidden"?: boolean | "true" | "false"
}>

interface StatCardProps {
  label: string
  value: string | number
  icon: IconComponent
  trend?: "up" | "down" | "neutral"
  subtitle?: string
}

export const StatCard = React.memo(function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  subtitle,
}: StatCardProps) {
  return (
    <Card className="p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <p className="truncate text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
            {label}
          </p>
          <p className="text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-gray-50">
            {value}
          </p>
          {subtitle && (
            <p className="truncate text-xs text-gray-500 dark:text-gray-400">
              {subtitle}
            </p>
          )}
        </div>
        <div
          className={cx(
            "flex size-10 shrink-0 items-center justify-center rounded-lg",
            trend === "up" &&
              "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400",
            trend === "down" &&
              "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400",
            (!trend || trend === "neutral") &&
              "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400",
          )}
        >
          <Icon aria-hidden="true" className="size-5" />
        </div>
      </div>
    </Card>
  )
})
