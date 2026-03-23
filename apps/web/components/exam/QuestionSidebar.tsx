"use client";

export type QuestionStatus =
  | "current"
  | "empty"
  | "answered"
  | "correct"
  | "wrong"
  | "skipped";

export function QuestionSidebar({
  total,
  currentIndex,
  getStatus,
  onSelectIndex,
  scrollable = false,
  maxHeightClassName = "max-h-[min(40vh,320px)] md:max-h-[calc(100dvh-15rem)]",
}: {
  total: number;
  currentIndex: number;
  getStatus: (q: number) => QuestionStatus;
  onSelectIndex: (index: number) => void;
  scrollable?: boolean;
  maxHeightClassName?: string;
}) {
  const questionGrid = (
    <div className="grid grid-cols-3 place-items-center gap-3 p-1 sm:gap-3.5">
      {Array.from({ length: total }, (_, i) => {
        const q = i + 1;
        const status = getStatus(q);
        const isCurrent = i === currentIndex;
        let cls =
          "min-h-[46px] min-w-[46px] rounded-xl border-2 text-base font-bold transition sm:min-h-[48px] sm:min-w-[48px]";
        if (status === "correct") {
          cls += " border-emerald-500 bg-emerald-500 text-white";
        } else if (status === "wrong") {
          cls += " border-red-500 bg-red-500 text-white";
        } else if (status === "answered" || status === "skipped") {
          cls += " border-blue-400 bg-blue-100 text-blue-900";
        } else {
          cls += " border-slate-200 bg-white text-slate-600";
        }
        if (isCurrent) {
          cls += " z-[1] ring-[3px] ring-amber-400 ring-offset-2 ring-offset-white";
        }
        return (
          <button
            key={q}
            type="button"
            onClick={() => onSelectIndex(i)}
            className={cls}
            aria-current={isCurrent ? "true" : undefined}
            aria-label={`Question ${q}`}
          >
            {q}
          </button>
        );
      })}
    </div>
  );

  return (
    <div className="w-full shrink-0">
      <div className="mx-auto w-full max-w-[220px]">
        <h2 className="mb-3 text-center text-xs font-bold uppercase tracking-wide text-slate-500">
          All questions
        </h2>
        {scrollable ? (
          <div
            className={`overflow-y-auto pr-1 [scrollbar-gutter:stable] ${maxHeightClassName}`}
          >
            {questionGrid}
          </div>
        ) : (
          questionGrid
        )}
      </div>
    </div>
  );
}
