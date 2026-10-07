"use client";

import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

type PracticeExitDialogProps = {
  open: boolean;
  /** 1-based question the learner is on. */
  questionNumber: number;
  onCancel: () => void;
  onKeep: () => void;
  onClear: () => void;
};

export function PracticeExitDialog({
  open,
  questionNumber,
  onCancel,
  onKeep,
  onClear,
}: PracticeExitDialogProps) {
  return (
    <ConfirmDialog
      open={open}
      title="Save your practice progress?"
      description={`You are on question ${questionNumber}. Keep your progress to continue next time, or clear it to start fresh from question 1.`}
      onCancel={onCancel}
      actions={[
        {
          label: "Keep and exit",
          variant: "primary",
          onClick: onKeep,
          initialFocus: true,
        },
        { label: "Clear and exit", variant: "danger-soft", onClick: onClear },
        { label: "Cancel", variant: "ghost", onClick: onCancel },
      ]}
    />
  );
}
