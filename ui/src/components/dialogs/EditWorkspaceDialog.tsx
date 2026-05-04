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
import { deleteWorkspace, updateWorkspace } from "@/lib/api/workspaces"
import type { WorkspaceResponse } from "@/lib/types/workspace"

interface EditWorkspaceDialogProps {
  workspace: WorkspaceResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved?: (ws: WorkspaceResponse) => void
  onDeleted?: (id: string) => void
}

const TEXTAREA_CLASSES =
  "block w-full resize-y rounded-md border border-gray-300 bg-white px-2.5 py-2 text-sm text-gray-900 placeholder-gray-400 shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-50 dark:placeholder-gray-500 dark:focus:ring-indigo-400/20"

export function EditWorkspaceDialog({
  workspace,
  open,
  onOpenChange,
  onSaved,
  onDeleted,
}: EditWorkspaceDialogProps) {
  const [name, setName] = React.useState("")
  const [color, setColor] = React.useState("#6366F1")
  const [description, setDescription] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [isDeleting, setIsDeleting] = React.useState(false)

  // Re-hydrate the form whenever a different workspace is opened.
  React.useEffect(() => {
    if (workspace) {
      setName(workspace.name)
      setColor(workspace.color)
      setDescription(workspace.description ?? "")
      setError(null)
    }
  }, [workspace])

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setError(null)
    }
    onOpenChange(next)
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!workspace) return
    setError(null)

    const trimmedName = name.trim()
    if (!trimmedName) {
      setError("Name is required.")
      return
    }

    setIsSubmitting(true)
    try {
      const saved = await updateWorkspace(workspace.id, {
        name: trimmedName,
        color,
        description: description.trim() || null,
      })
      onSaved?.(saved)
      onOpenChange(false)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Failed to update workspace.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!workspace) return
    if (workspace.isDefault) return
    setError(null)
    setIsDeleting(true)
    try {
      await deleteWorkspace(workspace.id)
      onDeleted?.(workspace.id)
      onOpenChange(false)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Failed to delete workspace.")
      }
    } finally {
      setIsDeleting(false)
    }
  }

  if (!workspace) return null

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-y-4">
          <DialogHeader>
            <DialogTitle>Edit workspace</DialogTitle>
            <DialogDescription>
              {workspace.isDefault
                ? "The built-in default workspace can be renamed but not deleted."
                : "Update name, color, or description."}
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-y-1.5">
            <Label htmlFor="ws-edit-name">Name</Label>
            <Input
              id="ws-edit-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-y-1.5">
            <Label htmlFor="ws-edit-color">Color</Label>
            <div className="flex items-center gap-x-3">
              <Input
                id="ws-edit-color"
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
            <Label htmlFor="ws-edit-description">Description</Label>
            <textarea
              id="ws-edit-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className={TEXTAREA_CLASSES}
            />
          </div>

          <DialogFooter className="sm:justify-between">
            {!workspace.isDefault ? (
              <Button
                type="button"
                variant="destructive"
                onClick={handleDelete}
                disabled={isSubmitting || isDeleting}
                isLoading={isDeleting}
                loadingText="Deleting..."
              >
                Delete
              </Button>
            ) : (
              <span />
            )}
            <div className="flex gap-x-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => handleOpenChange(false)}
                disabled={isSubmitting || isDeleting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                isLoading={isSubmitting}
                loadingText="Saving..."
                disabled={isDeleting}
              >
                Save
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default EditWorkspaceDialog
