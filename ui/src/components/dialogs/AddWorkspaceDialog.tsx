"use client"

import React from "react"

import { Button } from "@/components/Button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/Dialog"
import { Input } from "@/components/Input"
import { Label } from "@/components/Label"
import { ApiError } from "@/lib/api/client"
import { createWorkspace } from "@/lib/api/workspaces"
import type { WorkspaceResponse } from "@/lib/types/workspace"

interface AddWorkspaceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (ws: WorkspaceResponse) => void
}

const DEFAULT_COLOR = "#6366F1"
const TEXTAREA_CLASSES =
  "block w-full resize-y rounded-md border border-gray-300 bg-white px-2.5 py-2 text-sm text-gray-900 placeholder-gray-400 shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-50 dark:placeholder-gray-500 dark:focus:ring-indigo-400/20"

export function AddWorkspaceDialog({
  open,
  onOpenChange,
  onSuccess,
}: AddWorkspaceDialogProps) {
  const [name, setName] = React.useState("")
  const [color, setColor] = React.useState(DEFAULT_COLOR)
  const [description, setDescription] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const reset = () => {
    setName("")
    setColor(DEFAULT_COLOR)
    setDescription("")
    setError(null)
  }

  const handleOpenChange = (next: boolean) => {
    if (!next) reset()
    onOpenChange(next)
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    const trimmedName = name.trim()
    if (!trimmedName) {
      setError("Name is required.")
      return
    }

    setIsSubmitting(true)
    try {
      const created = await createWorkspace({
        name: trimmedName,
        color,
        description: description.trim() || null,
      })
      reset()
      onSuccess?.(created)
      onOpenChange(false)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Failed to create workspace.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-y-4">
          <DialogHeader>
            <DialogTitle>Add workspace</DialogTitle>
            <DialogDescription>
              Group Aerospike clusters managed by your team into a workspace.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-y-1.5">
            <Label htmlFor="ws-name">Name</Label>
            <Input
              id="ws-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="team-a"
              autoFocus
              required
            />
          </div>

          <div className="flex flex-col gap-y-1.5">
            <Label htmlFor="ws-color">Color</Label>
            <div className="flex items-center gap-x-3">
              <Input
                id="ws-color"
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="h-9 w-16 cursor-pointer p-1"
              />
              <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                {color}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-y-1.5">
            <Label htmlFor="ws-description">Description</Label>
            <textarea
              id="ws-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="What's this workspace for?"
              className={TEXTAREA_CLASSES}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
            >
              Go back
            </Button>
            <Button
              type="submit"
              isLoading={isSubmitting}
              loadingText="Creating..."
            >
              Add workspace
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default AddWorkspaceDialog
