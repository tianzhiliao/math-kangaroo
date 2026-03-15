import { useCallback, useEffect, useRef, useState } from 'react'
import { cn } from '../lib/utils'
import { useUiFeedback } from '../context/UIFeedbackContext'
import type { UIFeedbackKind } from '../audio/uiFeedbackController'

const FEEDBACK_DURATIONS: Record<UIFeedbackKind, number> = {
  nav: 180,
  primary: 220,
  utility: 160,
  danger: 260,
}

export function useUiFeedbackPress(kind: UIFeedbackKind) {
  const { playFeedback, reducedMotion } = useUiFeedback()
  const [isFeedbacking, setIsFeedbacking] = useState(false)
  const timeoutRef = useRef<number | null>(null)

  const triggerFeedback = useCallback(() => {
    playFeedback(kind)

    if (reducedMotion) {
      return
    }

    setIsFeedbacking(true)
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current)
    }

    timeoutRef.current = window.setTimeout(() => {
      setIsFeedbacking(false)
      timeoutRef.current = null
    }, FEEDBACK_DURATIONS[kind])
  }, [kind, playFeedback, reducedMotion])

  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return {
    triggerFeedback,
    feedbackClassName: cn('ui-feedback', `ui-feedback--${kind}`, isFeedbacking && 'ui-feedback--active'),
  }
}
