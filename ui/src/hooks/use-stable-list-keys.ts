"use client"

import { useRef } from "react"

/**
 * Maintains a parallel array of stable React keys for an externally
 * controlled, append/remove-only list. Use to key Stepper editable
 * lists whose entries serialize into a server-payload type and have
 * no natural id of their own. The consumer must call
 * `notifyAdd()` / `notifyRemove(i)` whenever the source list grows
 * or shrinks so the parallel keys array stays index-aligned.
 *
 * Why: keying such lists by `index` causes focus, IME composition,
 * and uncontrolled DOM state to leak from a removed entry into the
 * surviving entry that takes its slot.
 */
export function useStableListKeys(currentLength: number) {
  const keysRef = useRef<string[]>([])

  // Defensive realignment if the source array changes outside the
  // notify* helpers (e.g., form prefill on first render, async fill).
  while (keysRef.current.length < currentLength) {
    keysRef.current.push(crypto.randomUUID())
  }
  if (keysRef.current.length > currentLength) {
    keysRef.current = keysRef.current.slice(0, currentLength)
  }

  const notifyAdd = () => {
    keysRef.current = [...keysRef.current, crypto.randomUUID()]
  }
  const notifyRemove = (i: number) => {
    keysRef.current = keysRef.current.filter((_, idx) => idx !== i)
  }

  return { keys: keysRef.current, notifyAdd, notifyRemove }
}
