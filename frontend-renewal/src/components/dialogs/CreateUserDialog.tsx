"use client"

import React from "react"

import { Button } from "@/components/Button"
import { Checkbox } from "@/components/Checkbox"
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
import type { AerospikeRole, CreateUserRequest } from "@/lib/types/admin"

const AVAILABLE_PRIVILEGES = [
  "read",
  "write",
  "read-write",
  "read-write-udf",
  "sys-admin",
  "user-admin",
  "data-admin",
]

interface CreateUserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  roles: AerospikeRole[]
  onSubmit: (body: CreateUserRequest) => Promise<void>
}

export function CreateUserDialog({
  open,
  onOpenChange,
  roles,
  onSubmit,
}: CreateUserDialogProps) {
  const [username, setUsername] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [selected, setSelected] = React.useState<string[]>([])
  const [error, setError] = React.useState<string | null>(null)
  const [submitting, setSubmitting] = React.useState(false)

  const reset = React.useCallback(() => {
    setUsername("")
    setPassword("")
    setSelected([])
    setError(null)
    setSubmitting(false)
  }, [])

  const handleOpenChange = (next: boolean) => {
    if (!next) reset()
    onOpenChange(next)
  }

  const toggle = (role: string) =>
    setSelected((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role],
    )

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    const u = username.trim()
    if (!u) {
      setError("Username is required.")
      return
    }
    if (!password) {
      setError("Password is required.")
      return
    }

    setSubmitting(true)
    try {
      await onSubmit({ username: u, password, roles: selected })
      reset()
      onOpenChange(false)
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail || err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Failed to create user.")
    } finally {
      setSubmitting(false)
    }
  }

  // Fall back to privilege codes as role options if the cluster has no roles
  // (common in first-time setup).
  const items =
    roles.length > 0
      ? roles.map((r) => ({ id: r.name, label: r.name }))
      : AVAILABLE_PRIVILEGES.map((p) => ({ id: p, label: p }))

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-y-4">
          <DialogHeader>
            <DialogTitle>Create user</DialogTitle>
            <DialogDescription>
              Create a new Aerospike user and assign roles.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-y-1.5">
            <Label htmlFor="user-username">Username</Label>
            <Input
              id="user-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="username"
              autoComplete="off"
              autoFocus
              required
            />
          </div>

          <div className="flex flex-col gap-y-1.5">
            <Label htmlFor="user-password">Password</Label>
            <Input
              id="user-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="password"
              autoComplete="new-password"
              required
            />
          </div>

          <div className="flex flex-col gap-y-1.5">
            <Label>Roles</Label>
            <div className="max-h-48 space-y-2 overflow-auto rounded-md border border-gray-200 p-3 dark:border-gray-800">
              {items.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No roles available.
                </p>
              ) : (
                items.map((item) => (
                  <div key={item.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`urole-${item.id}`}
                      checked={selected.includes(item.id)}
                      onCheckedChange={() => toggle(item.id)}
                    />
                    <Label
                      htmlFor={`urole-${item.id}`}
                      className="cursor-pointer text-sm font-normal"
                    >
                      {item.label}
                    </Label>
                  </div>
                ))
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleOpenChange(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={submitting}
              loadingText="Creating..."
              disabled={submitting || !username.trim() || !password}
            >
              Create user
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default CreateUserDialog
