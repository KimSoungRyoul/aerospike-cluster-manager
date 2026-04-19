"use client"

import { useEffect } from "react"
import { useUiStore } from "@/stores/ui-store"

/**
 * Register global keyboard shortcuts.
 *
 * Currently wired:
 *   - Cmd/Ctrl + B → toggle sidebar
 */
export function useKeyboardShortcuts() {
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.metaKey || e.ctrlKey) {
        switch (e.key) {
          case "b":
            e.preventDefault()
            toggleSidebar()
            break
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [toggleSidebar])
}
