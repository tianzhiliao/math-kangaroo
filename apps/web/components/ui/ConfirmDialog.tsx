"use client";

import { useEffect, useId, useRef } from "react";
import { Button, type ButtonVariant } from "./Button";

export type DialogAction = {
  label: string;
  variant: ButtonVariant;
  onClick: () => void;
  /** Receives focus when the dialog opens — use for the safe choice. */
  initialFocus?: boolean;
};

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Modal confirm dialog (plan-c.md §5.11): Esc and the scrim cancel, focus is
 * trapped inside and returns to the trigger on close. Actions stack full-width,
 * primary first.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  actions,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: React.ReactNode;
  actions: DialogAction[];
  onCancel: () => void;
}) {
  const titleId = useId();
  const descId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const initialRef = useRef<HTMLButtonElement>(null);
  const onCancelRef = useRef(onCancel);
  onCancelRef.current = onCancel;

  useEffect(() => {
    if (!open) return;
    const trigger =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    (initialRef.current ?? panelRef.current)?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancelRef.current();
        return;
      }
      if (e.key !== "Tab" || !panelRef.current) return;
      const items = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE),
      );
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      if (trigger?.isConnected) trigger.focus();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div
        className="mk-fade-in absolute inset-0 bg-mk-scrim"
        aria-hidden
        onClick={onCancel}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        tabIndex={-1}
        className="mk-pop-in relative w-full max-w-[480px] rounded-panel border border-mk-ink-12 bg-mk-bg p-7 shadow-popover"
      >
        <h2 id={titleId} className="text-h4">
          {title}
        </h2>
        <p id={descId} className="mt-2 text-p1 text-mk-ink-80">
          {description}
        </p>
        <div className="mt-6 flex flex-col gap-2">
          {actions.map((a) => (
            <Button
              key={a.label}
              ref={a.initialFocus ? initialRef : undefined}
              variant={a.variant}
              onClick={a.onClick}
              className="w-full"
            >
              {a.label}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}
