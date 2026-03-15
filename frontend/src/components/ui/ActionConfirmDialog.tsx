import * as React from 'react'
import { Sparkles, X } from 'lucide-react'
import { Button } from './Button'

interface ActionConfirmDialogProps {
  open: boolean
  title: string
  description: string
  accentLabel?: string
  primaryLabel: string
  secondaryLabel: string
  tertiaryLabel?: string
  onPrimary: () => void
  onSecondary: () => void
  onTertiary: () => void
}

export function ActionConfirmDialog({
  open,
  title,
  description,
  accentLabel,
  primaryLabel,
  secondaryLabel,
  tertiaryLabel = 'Stay here',
  onPrimary,
  onSecondary,
  onTertiary,
}: ActionConfirmDialogProps) {
  const panelRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (!open) {
      return
    }

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    panelRef.current?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onTertiary()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onTertiary, open])

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-[70]">
      <button
        type="button"
        aria-label="Close dialog"
        className="absolute inset-0 bg-slate-900/25 backdrop-blur-sm"
        onClick={onTertiary}
      />
      <div className="absolute inset-x-0 bottom-0 p-3 md:grid md:inset-0 md:place-items-center md:p-6">
        <div
          ref={panelRef}
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-labelledby="action-confirm-dialog-title"
          className="relative w-full rounded-t-[2rem] border border-white/80 bg-white px-5 pb-6 pt-5 shadow-[0_26px_80px_rgba(15,23,42,0.2)] outline-none md:max-w-md md:rounded-[2rem] md:px-6"
        >
          <div className="mb-5 flex items-start justify-between gap-4">
            <div className="space-y-3">
              {accentLabel && (
                <span className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.24em] text-primary">
                  <Sparkles className="h-3.5 w-3.5" />
                  {accentLabel}
                </span>
              )}
              <div className="space-y-2">
                <h2
                  id="action-confirm-dialog-title"
                  className="text-2xl font-black tracking-[-0.04em] text-slate-950"
                >
                  {title}
                </h2>
                <p className="text-sm font-medium leading-6 text-slate-500">{description}</p>
              </div>
            </div>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Close dialog"
              onClick={onTertiary}
              className="shrink-0"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          <div className="flex flex-col gap-3">
            <Button variant="primary" size="lg" fullWidth onClick={onPrimary}>
              {primaryLabel}
            </Button>
            <Button variant="danger" size="lg" fullWidth onClick={onSecondary}>
              {secondaryLabel}
            </Button>
            <Button variant="outline" size="lg" fullWidth feedbackKind="nav" onClick={onTertiary}>
              {tertiaryLabel}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
