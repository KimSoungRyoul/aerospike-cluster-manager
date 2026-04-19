"use client"

import {
  RiAlertLine,
  RiComputerLine,
  RiDatabase2Line,
  RiDeleteBin2Line,
  RiHardDrive2Line,
  RiInformationLine,
  RiMoonLine,
  RiServerLine,
  RiSunLine,
} from "@remixicon/react"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

import { Badge } from "@/components/Badge"
import { Card } from "@/components/Card"
import { PageHeader } from "@/components/common/PageHeader"
import { CE_LIMITS } from "@/lib/constants"
import { cx } from "@/lib/utils"

type Theme = "light" | "dark" | "system"

const themeOptions: {
  value: Theme
  label: string
  icon: React.ComponentType<{
    className?: string
    "aria-hidden"?: boolean | "true" | "false"
  }>
  description: string
}[] = [
  {
    value: "light",
    label: "Light",
    icon: RiSunLine,
    description: "Clean, bright interface",
  },
  {
    value: "dark",
    label: "Dark",
    icon: RiMoonLine,
    description: "Easy on the eyes",
  },
  {
    value: "system",
    label: "System",
    icon: RiComputerLine,
    description: "Follow OS preference",
  },
]

export default function SettingsPage() {
  const { theme = "system", setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  // `next-themes` hydrates on the client; avoid rendering until then so the
  // selected theme matches the active <html> class.
  useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Settings"
        description="Application preferences and information"
      />

      {/* Appearance */}
      <Card>
        <div className="space-y-1">
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-50">
            Appearance
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Customize the look and feel of the application
          </p>
        </div>
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {themeOptions.map((opt) => {
            const selected = mounted && theme === opt.value
            const Icon = opt.icon
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setTheme(opt.value)}
                className={cx(
                  "flex flex-col items-center gap-2 rounded-xl border-2 p-4 text-center transition-all duration-200",
                  selected
                    ? "border-indigo-500 bg-indigo-50/50 shadow-sm dark:border-indigo-500 dark:bg-indigo-500/10"
                    : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50 dark:border-gray-800 dark:hover:border-indigo-700 dark:hover:bg-gray-900/40",
                )}
                aria-pressed={selected}
              >
                <Icon
                  aria-hidden="true"
                  className={cx(
                    "size-6 transition-colors",
                    selected
                      ? "text-indigo-600 dark:text-indigo-400"
                      : "text-gray-500 dark:text-gray-400",
                  )}
                />
                <div>
                  <span
                    className={cx(
                      "block text-sm font-medium",
                      selected
                        ? "text-indigo-600 dark:text-indigo-400"
                        : "text-gray-900 dark:text-gray-100",
                    )}
                  >
                    {opt.label}
                  </span>
                  <span className="mt-0.5 block text-[11px] text-gray-500 dark:text-gray-400">
                    {opt.description}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </Card>

      {/* CE Limitations */}
      <Card>
        <div className="space-y-1">
          <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900 dark:text-gray-50">
            <RiAlertLine
              className="size-4 text-yellow-500 dark:text-yellow-400"
              aria-hidden="true"
            />
            Aerospike CE Limitations
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Community Edition restrictions to be aware of
          </p>
        </div>
        <div className="mt-5 space-y-2">
          <LimitRow
            icon={RiServerLine}
            title="Max Nodes per Cluster"
            description="Cluster cannot exceed this node count"
            value={
              <Badge variant="neutral" className="font-mono">
                {CE_LIMITS.MAX_NODES}
              </Badge>
            }
          />
          <LimitRow
            icon={RiDatabase2Line}
            title="Max Namespaces"
            description="Maximum number of namespaces per cluster"
            value={
              <Badge variant="neutral" className="font-mono">
                {CE_LIMITS.MAX_NAMESPACES}
              </Badge>
            }
          />
          <LimitRow
            icon={RiHardDrive2Line}
            title="Max Data Capacity"
            description="Approximately 5TB total (2.5TB unique data)"
            value={
              <Badge variant="neutral" className="font-mono">
                ~{CE_LIMITS.MAX_DATA_TB} TB
              </Badge>
            }
          />
          <LimitRow
            icon={RiDeleteBin2Line}
            title="Durable Deletes"
            description="Deletes not persistent across cold restarts"
            value={
              <Badge variant="error" className="text-[11px]">
                Not Supported
              </Badge>
            }
          />
          <LimitRow
            icon={RiServerLine}
            title="XDR (Cross Datacenter Replication)"
            description="Enterprise-only feature"
            value={
              <Badge variant="error" className="text-[11px]">
                Not Supported
              </Badge>
            }
          />
        </div>
      </Card>

      {/* About */}
      <Card>
        <div className="flex items-center gap-2">
          <RiInformationLine
            className="size-4 text-indigo-500 dark:text-indigo-400"
            aria-hidden="true"
          />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-50">
            About
          </h2>
        </div>
        <dl className="mt-5 divide-y divide-gray-200 text-sm dark:divide-gray-800">
          <AboutRow label="Application" value="Aerospike Cluster Manager" />
          <AboutRow label="Version" value="0.1.0" mono />
          <AboutRow label="Framework" value="Next.js 14" mono />
          <AboutRow
            label="UI Library"
            value="Tailwind CSS 3 + Tremor Raw"
            mono
          />
          <AboutRow label="Backend Client" value="aerospike-py" mono />
          <AboutRow
            label="Observability"
            value="OpenTelemetry / Prometheus"
            mono
          />
        </dl>
        <p className="mt-4 rounded-md bg-gray-50 px-3.5 py-3 text-xs leading-relaxed text-gray-500 dark:bg-gray-900/40 dark:text-gray-400">
          This application is designed for managing Aerospike Community Edition
          clusters. It provides data browsing, query building, index management,
          user/role administration, UDF management, and OTel-based observability
          through a modern web interface.
        </p>
      </Card>
    </div>
  )
}

function LimitRow({
  icon: Icon,
  title,
  description,
  value,
}: {
  icon: React.ComponentType<{
    className?: string
    "aria-hidden"?: boolean | "true" | "false"
  }>
  title: string
  description: string
  value: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between rounded-md border border-gray-200 px-4 py-3 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900/30">
      <div className="flex items-center gap-3">
        <Icon
          className="size-4 text-gray-500 dark:text-gray-400"
          aria-hidden="true"
        />
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-gray-50">
            {title}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {description}
          </p>
        </div>
      </div>
      {value}
    </div>
  )
}

function AboutRow({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex justify-between py-2">
      <dt className="text-gray-500 dark:text-gray-400">{label}</dt>
      <dd
        className={cx(
          "text-gray-900 dark:text-gray-50",
          mono && "font-mono text-xs",
        )}
      >
        {value}
      </dd>
    </div>
  )
}
