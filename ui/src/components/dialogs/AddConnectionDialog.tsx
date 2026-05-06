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
import { ConnectionFormFields } from "@/components/dialogs/ConnectionFormFields"
import { useConnectionForm } from "@/components/dialogs/useConnectionForm"
import { useWorkspaces } from "@/hooks/use-workspaces"
import { ApiError } from "@/lib/api/client"
import { createConnection } from "@/lib/api/connections"
import { bumpConnectionsRev } from "@/stores/data-revision-store"
import { useUiStore } from "@/stores/ui-store"

interface AddConnectionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function AddConnectionDialog({
  open,
  onOpenChange,
  onSuccess,
}: AddConnectionDialogProps) {
  const { form, setForm, validate, reset } = useConnectionForm()
  const [error, setError] = React.useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const { data: workspaces } = useWorkspaces()

  // Default the selector to the workspace the user is currently viewing
  // when the dialog opens. Reading currentWorkspaceId via getState() inside
  // the effect (instead of as a dep) avoids clobbering the user's explicit
  // selection when they switch workspaces in the sidebar while the dialog
  // is still open.
  React.useEffect(() => {
    if (!open) return
    setForm((prev) => ({
      ...prev,
      workspaceId: useUiStore.getState().currentWorkspaceId,
    }))
  }, [open, setForm])

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      reset()
      setError(null)
    }
    onOpenChange(next)
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    const result = validate()
    if (!result.ok) {
      setError(result.error)
      return
    }

    setIsSubmitting(true)
    try {
      await createConnection(result.payload)
      bumpConnectionsRev()
      reset()
      onSuccess?.()
      onOpenChange(false)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Failed to create connection.")
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
            <DialogTitle>Add connection</DialogTitle>
            <DialogDescription>
              Register a new Aerospike cluster connection profile.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          <ConnectionFormFields
            form={form}
            setForm={setForm}
            idPrefix="conn"
            workspaces={workspaces}
          />

          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={isSubmitting}
              loadingText="Creating..."
            >
              Create
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default AddConnectionDialog
