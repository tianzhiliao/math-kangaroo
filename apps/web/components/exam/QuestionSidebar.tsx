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
}: {
  total: number;
  currentIndex: number;
  getStatus: (q: number) => QuestionStatus;
  onSelectIndex: (index: number) => void;
}) {
  return (
    <div className="w-full shrink-0 md:w-52">
      <h2 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-500">
        All questions
      </h2>
      {/* Extra padding on mobile so ring/ring-offset is not clipped by overflow-x; wider gaps so tiles breathe */}
      <div
        className="-mx-1 flex max-w-none gap-3 overflow-x-auto scroll-pl-3 scroll-pr-3 px-3 py-2.5 md:mx-0 md:max-w-full md:gap-3.5 md:flex-wrap md:overflow-visible md:px-0 md:py-1 md:scroll-pl-0 md:scroll-pr-0"
      >
        {Array.from({ length: total }, (_, i) => {
          const q = i + 1;
          const status = getStatus(q);
          const isCurrent = i === currentIndex;
          let cls =
            "shrink-0 min-h-[46px] min-w-[46px] rounded-xl border-2 text-base font-bold transition sm:min-h-[48px] sm:min-w-[48px]";
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
            cls +=
              " z-[1] ring-[3px] ring-amber-400 ring-offset-2 ring-offset-white";
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
    </div>
  );
}
