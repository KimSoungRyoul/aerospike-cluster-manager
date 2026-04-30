"use client"

import { Button } from "@/components/Button"
import { Input } from "@/components/Input"
import { Label } from "@/components/Label"
import { cx } from "@/lib/utils"
import { RiAddLine, RiDeleteBinLine } from "@remixicon/react"
import React from "react"

export type LabelEntry = { key: string; value: string }

export const ENV_LABEL_KEY = "env"
export const DEFAULT_ENV_VALUE = "default"

export function labelsToEntries(labels: Record<string, string>): LabelEntry[] {
  const entries: LabelEntry[] = [
    { key: ENV_LABEL_KEY, value: labels[ENV_LABEL_KEY] ?? DEFAULT_ENV_VALUE },
  ]
  for (const [k, v] of Object.entries(labels)) {
    if (k === ENV_LABEL_KEY) continue
    entries.push({ key: k, value: v })
  }
  return entries
}

export function entriesToLabels(entries: LabelEntry[]): Record<string, string> {
  const out: Record<string, string> = {}
  for (const { key, value } of entries) {
    const k = key.trim()
    if (!k) continue
    out[k] = value
  }
  if (!out[ENV_LABEL_KEY]) {
    out[ENV_LABEL_KEY] = DEFAULT_ENV_VALUE
  }
  return out
}

interface LabelsEditorProps {
  value: LabelEntry[]
  onChange: (next: LabelEntry[]) => void
  idPrefix?: string
}

export function LabelsEditor({
  value,
  onChange,
  idPrefix = "label",
}: LabelsEditorProps) {
  const entries =
    value.length > 0
      ? value
      : [{ key: ENV_LABEL_KEY, value: DEFAULT_ENV_VALUE }]

  const update = (index: number, patch: Partial<LabelEntry>) => {
    const next = entries.map((entry, i) =>
      i === index ? { ...entry, ...patch } : entry,
    )
    onChange(next)
  }

  const remove = (index: number) => {
    if (entries[index]?.key === ENV_LABEL_KEY) return
    onChange(entries.filter((_, i) => i !== index))
  }

  const add = () => {
    onChange([...entries, { key: "", value: "" }])
  }

  return (
    <div className="flex flex-col gap-y-2">
      <div className="flex items-end justify-between">
        <Label>Labels</Label>
        <Button
          type="button"
          variant="ghost"
          className="h-7 px-2 text-xs"
          onClick={add}
        >
          <RiAddLine className="mr-1 size-3.5" aria-hidden="true" />
          Add label
        </Button>
      </div>
      <div className="flex flex-col gap-y-2">
        {entries.map((entry, index) => {
          const locked = entry.key === ENV_LABEL_KEY
          return (
            <div key={index} className="flex items-center gap-2">
              <Input
                aria-label={`${idPrefix} key ${index}`}
                value={entry.key}
                onChange={(e) => update(index, { key: e.target.value })}
                placeholder={locked ? ENV_LABEL_KEY : "key (e.g. idc)"}
                disabled={locked}
                className={cx("flex-1", locked && "opacity-70")}
              />
              <span className="text-gray-400" aria-hidden="true">
                =
              </span>
              <Input
                aria-label={`${idPrefix} value ${index}`}
                value={entry.value}
                onChange={(e) => update(index, { value: e.target.value })}
                placeholder={locked ? DEFAULT_ENV_VALUE : "value (e.g. 평촌)"}
                className="flex-1"
              />
              <Button
                type="button"
                variant="ghost"
                aria-label={
                  locked ? "env label cannot be removed" : "Remove label"
                }
                title={locked ? "env label cannot be removed" : "Remove label"}
                disabled={locked}
                onClick={() => remove(index)}
                className="h-9 px-2"
              >
                <RiDeleteBinLine className="size-4" aria-hidden="true" />
              </Button>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-500">
        The <code className="font-mono">env</code> label is required and used to
        group clusters in the list view.
      </p>
    </div>
  )
}

export default LabelsEditor
