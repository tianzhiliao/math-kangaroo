"use client";

type PracticeExitDialogProps = {
  open: boolean;
  onCancel: () => void;
  onKeep: () => void;
  onClear: () => void;
};

export function PracticeExitDialog({
  open,
  onCancel,
  onKeep,
  onClear,
}: PracticeExitDialogProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="practice-exit-title"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-xl">
        <h2
          id="practice-exit-title"
          className="text-lg font-bold text-slate-900"
        >
          Save your practice progress?
        </h2>
        <p className="mt-2 text-sm text-slate-700">
          Keep progress to continue next time, or clear progress to start fresh.
        </p>
        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex min-h-[40px] items-center justify-center rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onClear}
            className="inline-flex min-h-[40px] items-center justify-center rounded-xl bg-rose-100 px-4 py-2 text-sm font-semibold text-rose-800 transition hover:bg-rose-200"
          >
            Clear and exit
          </button>
          <button
            type="button"
            onClick={onKeep}
            className="inline-flex min-h-[40px] items-center justify-center rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700"
          >
            Keep and exit
          </button>
        </div>
      </div>
    </div>
  );
}
