import {
  RiErrorWarningLine,
  RiInformationLine,
  RiAlertLine,
} from "@remixicon/react"

import { cx } from "@/lib/utils"

type AlertVariant = "error" | "warning" | "info"

interface InlineAlertProps {
  message: string | null | undefined
  variant?: AlertVariant
  className?: string
}

const variantStyles: Record<AlertVariant, string> = {
  error:
    "border-red-200 bg-red-50 text-red-900 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200",
  warning:
    "border-yellow-200 bg-yellow-50 text-yellow-900 dark:border-yellow-900/50 dark:bg-yellow-950/30 dark:text-yellow-200",
  info: "border-indigo-200 bg-indigo-50 text-indigo-900 dark:border-indigo-900/50 dark:bg-indigo-950/30 dark:text-indigo-200",
}

const variantIcons: Record<AlertVariant, typeof RiInformationLine> = {
  error: RiErrorWarningLine,
  warning: RiAlertLine,
  info: RiInformationLine,
}

export function InlineAlert({
  message,
  variant = "error",
  className,
}: InlineAlertProps) {
  if (!message) return null
  const Icon = variantIcons[variant]

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cx(
        "flex items-start gap-2 rounded-md border px-3 py-2 text-sm",
        variantStyles[variant],
        className,
      )}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span className="leading-5">{message}</span>
    </div>
  )
}
