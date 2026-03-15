import * as React from "react"
import { cn } from "../../lib/utils"
import { useUiFeedbackPress } from "../../hooks/useUiFeedbackPress"
import type { UIFeedbackKind } from "../../audio/uiFeedbackController"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "danger" | "outline" | "ghost"
  size?: "default" | "lg" | "icon"
  fullWidth?: boolean
  feedbackKind?: UIFeedbackKind
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "default",
      fullWidth = false,
      feedbackKind,
      onClick,
      disabled,
      ...props
    },
    ref
  ) => {
    const resolvedFeedbackKind =
      feedbackKind ??
      (variant === "primary"
        ? "primary"
        : variant === "danger"
          ? "danger"
          : "utility")
    const { feedbackClassName, triggerFeedback } = useUiFeedbackPress(resolvedFeedbackKind)

    const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      if (!disabled) {
        triggerFeedback()
      }

      onClick?.(event)
    }

    return (
      <button
        className={cn(
          feedbackClassName,
          "inline-flex items-center justify-center whitespace-nowrap rounded-[1.2rem] font-bold ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/50 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer",
          {
            "bg-primary text-white hover:bg-primary/95 shadow-[0_8px_18px_rgba(88,204,2,0.22)] active:translate-y-[2px] active:shadow-[0_4px_10px_rgba(88,204,2,0.18)]": variant === "primary",
            "bg-danger text-white hover:bg-danger/95 shadow-[0_8px_18px_rgba(255,107,130,0.22)] active:translate-y-[2px] active:shadow-[0_4px_10px_rgba(255,107,130,0.18)]": variant === "danger",
            "border-2 border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-[0_6px_16px_rgba(148,163,184,0.1)] active:translate-y-[2px] active:shadow-[0_2px_8px_rgba(148,163,184,0.12)]": variant === "outline",
            "hover:bg-white/80 text-slate-700": variant === "ghost",
          },
          {
            "h-11 px-4 py-2": size === "default",
            "h-14 px-8 text-lg": size === "lg",
            "h-11 w-11": size === "icon",
          },
          fullWidth && "w-full",
          className
        )}
        ref={ref}
        disabled={disabled}
        onClick={handleClick}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
