"use client"

import { RiArrowDownSLine, RiArrowRightSLine } from "@remixicon/react"
import { useState } from "react"

import { cx } from "@/lib/utils"

interface JsonViewerProps {
  data: unknown
  collapsed?: boolean
  level?: number
  className?: string
}

export function JsonViewer({
  data,
  collapsed = false,
  level = 0,
  className,
}: JsonViewerProps) {
  const [isCollapsed, setIsCollapsed] = useState(collapsed && level > 0)

  if (data === null)
    return <span className="text-gray-500 dark:text-gray-400">null</span>
  if (data === undefined)
    return <span className="text-gray-500 dark:text-gray-400">undefined</span>

  if (typeof data === "string") {
    return (
      <span className="text-emerald-700 dark:text-emerald-400">
        &quot;{data}&quot;
      </span>
    )
  }

  if (typeof data === "number") {
    return <span className="text-blue-700 dark:text-blue-400">{data}</span>
  }

  if (typeof data === "boolean") {
    return (
      <span className="text-purple-700 dark:text-purple-400">
        {data.toString()}
      </span>
    )
  }

  const toggleIcon = isCollapsed ? (
    <RiArrowRightSLine className="size-3" aria-hidden="true" />
  ) : (
    <RiArrowDownSLine className="size-3" aria-hidden="true" />
  )

  if (Array.isArray(data)) {
    if (data.length === 0)
      return <span className="text-gray-500 dark:text-gray-400">[]</span>

    return (
      <span className={cx("font-mono text-sm", className)}>
        <button
          type="button"
          onClick={() => setIsCollapsed((v) => !v)}
          className="inline-flex items-center hover:text-indigo-600 dark:hover:text-indigo-400"
          aria-expanded={!isCollapsed}
          aria-label={isCollapsed ? "Expand JSON array" : "Collapse JSON array"}
        >
          {toggleIcon}
        </button>
        {isCollapsed ? (
          <span className="text-gray-500 dark:text-gray-400">
            {" "}
            [{data.length} items]
          </span>
        ) : (
          <>
            {"["}
            <div className="ml-4">
              {data.map((item, i) => (
                <div key={i}>
                  <JsonViewer
                    data={item}
                    collapsed={collapsed}
                    level={level + 1}
                  />
                  {i < data.length - 1 && ","}
                </div>
              ))}
            </div>
            {"]"}
          </>
        )}
      </span>
    )
  }

  if (typeof data === "object") {
    const entries = Object.entries(data as Record<string, unknown>)
    if (entries.length === 0)
      return <span className="text-gray-500 dark:text-gray-400">{"{}"}</span>

    return (
      <span className={cx("font-mono text-sm", className)}>
        <button
          type="button"
          onClick={() => setIsCollapsed((v) => !v)}
          className="inline-flex items-center hover:text-indigo-600 dark:hover:text-indigo-400"
          aria-expanded={!isCollapsed}
          aria-label={
            isCollapsed ? "Expand JSON object" : "Collapse JSON object"
          }
        >
          {toggleIcon}
        </button>
        {isCollapsed ? (
          <span className="text-gray-500 dark:text-gray-400">
            {" "}
            {"{"}…{entries.length} keys{"}"}
          </span>
        ) : (
          <>
            {"{"}
            <div className="ml-4">
              {entries.map(([key, value], i) => (
                <div key={key}>
                  <span className="text-red-600 dark:text-red-400">
                    &quot;{key}&quot;
                  </span>
                  {": "}
                  <JsonViewer
                    data={value}
                    collapsed={collapsed}
                    level={level + 1}
                  />
                  {i < entries.length - 1 && ","}
                </div>
              ))}
            </div>
            {"}"}
          </>
        )}
      </span>
    )
  }

  return <span>{String(data)}</span>
}
