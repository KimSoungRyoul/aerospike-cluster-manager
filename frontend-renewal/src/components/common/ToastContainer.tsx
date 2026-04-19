"use client"

import {
  RiCheckLine,
  RiCloseLine,
  RiErrorWarningLine,
  RiInformationLine,
} from "@remixicon/react"

import { cx } from "@/lib/utils"
import { useToastStore, type ToastType } from "@/stores/toast-store"

const toastStyles: Record<
  ToastType,
  { container: string; icon: React.ElementType }
> = {
  success: {
    container:
      "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-200",
    icon: RiCheckLine,
  },
  error: {
    container:
      "border-red-200 bg-red-50 text-red-900 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200",
    icon: RiErrorWarningLine,
  },
  warning: {
    container:
      "border-yellow-200 bg-yellow-50 text-yellow-900 dark:border-yellow-900/50 dark:bg-yellow-950/40 dark:text-yellow-200",
    icon: RiErrorWarningLine,
  },
  info: {
    container:
      "border-indigo-200 bg-indigo-50 text-indigo-900 dark:border-indigo-900/50 dark:bg-indigo-950/40 dark:text-indigo-200",
    icon: RiInformationLine,
  },
}

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)
  const removeToast = useToastStore((s) => s.removeToast)

  if (toasts.length === 0) return null

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-[70] flex flex-col items-end gap-2 p-4 sm:bottom-4 sm:right-4 sm:items-end sm:p-0"
    >
      {toasts.map((t) => {
        const { container, icon: Icon } = toastStyles[t.type]
        return (
          <div
            key={t.id}
            role="status"
            className={cx(
              "pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-md border px-4 py-3 shadow-lg",
              container,
            )}
          >
            <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span className="flex-1 text-sm leading-5">{t.message}</span>
            <button
              type="button"
              onClick={() => removeToast(t.id)}
              className="inline-flex size-6 shrink-0 items-center justify-center rounded-full transition hover:bg-black/5 dark:hover:bg-white/10"
              aria-label="Dismiss notification"
            >
              <RiCloseLine className="size-3.5" aria-hidden="true" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
