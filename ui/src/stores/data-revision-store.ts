/**
 * Data revision store — monotonic counters that all `useConnections` /
 * `useWorkspaces` hook instances watch so a mutation in one component
 * (e.g. AddConnectionDialog) refetches every other instance (e.g. the
 * sidebar's WorkspacesDropdown). Without this each hook keeps a private
 * snapshot, leaving the dropdown's "hide empty Default" check stale until
 * the next page navigation.
 *
 * Bump from any place that creates / updates / deletes the corresponding
 * resource. Reads are intentionally cheap (just an integer); the actual
 * fetch happens inside the hooks.
 */

import { create } from "zustand"

interface DataRevisionStore {
  connectionsRev: number
  workspacesRev: number
  bumpConnections: () => void
  bumpWorkspaces: () => void
}

export const useDataRevisionStore = create<DataRevisionStore>((set) => ({
  connectionsRev: 0,
  workspacesRev: 0,
  bumpConnections: () => set((s) => ({ connectionsRev: s.connectionsRev + 1 })),
  bumpWorkspaces: () => set((s) => ({ workspacesRev: s.workspacesRev + 1 })),
}))

/** Imperative bumpers for use outside React (callbacks, async chains). */
export const bumpConnectionsRev = (): void =>
  useDataRevisionStore.getState().bumpConnections()

export const bumpWorkspacesRev = (): void =>
  useDataRevisionStore.getState().bumpWorkspaces()
