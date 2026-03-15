/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { FC, ReactNode } from 'react'
import { uiFeedbackController, type UIFeedbackKind } from '../audio/uiFeedbackController'

interface UIFeedbackContextType {
  reducedMotion: boolean
  playFeedback: (kind: UIFeedbackKind) => void
}

const UIFeedbackContext = createContext<UIFeedbackContextType | undefined>(undefined)

export const useUiFeedback = () => {
  const context = useContext(UIFeedbackContext)
  if (!context) {
    throw new Error('useUiFeedback must be used within a UIFeedbackProvider')
  }
  return context
}

interface UIFeedbackProviderProps {
  children: ReactNode
}

export const UIFeedbackProvider: FC<UIFeedbackProviderProps> = ({ children }) => {
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const syncPreference = () => {
      setReducedMotion(mediaQuery.matches)
    }

    syncPreference()
    mediaQuery.addEventListener('change', syncPreference)

    return () => {
      mediaQuery.removeEventListener('change', syncPreference)
    }
  }, [])

  const playFeedback = useCallback((kind: UIFeedbackKind) => {
    uiFeedbackController.play(kind)
  }, [])

  const value = useMemo(
    () => ({
      reducedMotion,
      playFeedback,
    }),
    [playFeedback, reducedMotion],
  )

  return <UIFeedbackContext.Provider value={value}>{children}</UIFeedbackContext.Provider>
}
