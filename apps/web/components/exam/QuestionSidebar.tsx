"use client";

import { useEffect, useRef } from "react";

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
  const mobileScrollRef = useRef<HTMLDivElement>(null);

  const questionButtons = Array.from({ length: total }, (_, i) => {
    const q = i + 1;
    const status = getStatus(q);
    const isCurrent = i === currentIndex;
    let cls =
      "rounded-xl border-2 text-base font-bold transition min-h-[42px] min-w-[42px] sm:min-h-[44px] sm:min-w-[44px] md:min-h-[48px] md:min-w-[48px]";
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
        data-question-index={i}
        onClick={() => onSelectIndex(i)}
        className={cls}
        aria-current={isCurrent ? "true" : undefined}
        aria-label={`Question ${q}`}
      >
        {q}
      </button>
    );
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(max-width: 767px)");
    if (!mq.matches) return;
    const root = mobileScrollRef.current;
    if (!root) return;
    const el = root.querySelector<HTMLElement>(
      `[data-question-index="${currentIndex}"]`,
    );
    el?.scrollIntoView({
      inline: "center",
      block: "nearest",
      behavior: "smooth",
    });
  }, [currentIndex]);

  const desktopQuestionGrid = (
    <div className="grid grid-cols-3 place-items-center gap-3 p-1 sm:gap-3.5">
      {questionButtons}
    </div>
  );

  const mobileQuestionRow = (
    <div
      ref={mobileScrollRef}
      className="-mx-1 overflow-x-auto overscroll-x-contain py-4 [scrollbar-gutter:stable]"
    >
      <div className="flex w-max items-center gap-2 px-1 sm:gap-2.5">
        {questionButtons}
      </div>
    </div>
  );

  return (
    <div className="w-full shrink-0">
      <div className="mx-auto w-full md:max-w-[220px]">
        <h2 className="mb-3 text-center text-xs font-bold uppercase tracking-wide text-slate-500">
          All questions
        </h2>
        <div className="md:hidden">{mobileQuestionRow}</div>
        <div className="hidden md:block">
          {scrollable ? (
            <div
              className={`overflow-y-auto pr-1 [scrollbar-gutter:stable] ${maxHeightClassName}`}
            >
              {desktopQuestionGrid}
            </div>
          ) : (
            desktopQuestionGrid
          )}
        </div>
      </div>
    </div>
  );
}
