"use client"

import { useState, useEffect, useRef } from "react"

type ScrollDirection = "up" | "down" | null

export function useScrollDirection(threshold = 10): ScrollDirection {
  const [direction, setDirection] = useState<ScrollDirection>(null)
  const lastY = useRef(0)
  const ticking = useRef(false)

  useEffect(() => {
    lastY.current = window.scrollY

    function update() {
      const currentY = window.scrollY
      const diff = currentY - lastY.current

      if (Math.abs(diff) >= threshold) {
        setDirection(diff > 0 ? "down" : "up")
        lastY.current = currentY
      }
      ticking.current = false
    }

    function onScroll() {
      if (!ticking.current) {
        requestAnimationFrame(update)
        ticking.current = true
      }
    }

    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [threshold])

  return direction
}
