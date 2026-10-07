"use client";

import { useEffect, useRef } from "react";
import { StatusLegend, type LegendItem } from "./StatusLegend";

export type QuestionStatus =
  | "current"
  | "empty"
  | "answered"
  | "correct"
  | "wrong"
  | "skipped";

const STATUS_CLASS: Record<QuestionStatus, string> = {
  current: "bg-mk-ink-100 text-mk-inverse",
  empty:
    "border border-mk-ink-12 bg-mk-bg text-mk-ink-60 hover:border-mk-ink-44",
  answered: "bg-mk-solid-12 text-mk-ink-100",
  correct: "bg-mk-right-soft text-mk-right-fg",
  wrong: "bg-mk-wrong-soft text-mk-wrong-fg",
  skipped:
    "border border-dashed border-mk-ink-44 bg-mk-bg text-mk-ink-60 hover:border-mk-ink-60",
};

const STATUS_LABEL: Record<QuestionStatus, string> = {
  current: "",
  empty: "not answered",
  answered: "answered",
  correct: "right",
  wrong: "wrong",
  skipped: "skipped",
};

/**
 * Question number grid (desktop) / horizontal strip (phone), plan-c.md §5.5.
 * `currentStyle="fill"` paints the current number black (exam in progress);
 * `"outline"` keeps its status colour and adds a black ring (practice, results).
 */
export function QuestionSidebar({
  total,
  currentIndex,
  getStatus,
  onSelectIndex,
  currentStyle = "outline",
  countLabel,
  legend,
  scrollable = false,
  maxHeightClassName = "md:max-h-[calc(100dvh-15rem)]",
}: {
  total: number;
  currentIndex: number;
  getStatus: (q: number) => QuestionStatus;
  onSelectIndex: (index: number) => void;
  currentStyle?: "fill" | "outline";
  countLabel?: string;
  legend?: LegendItem[];
  scrollable?: boolean;
  maxHeightClassName?: string;
}) {
  const mobileScrollRef = useRef<HTMLDivElement>(null);
  const desktopScrollRef = useRef<HTMLDivElement>(null);

  const questionButtons = Array.from({ length: total }, (_, i) => {
    const q = i + 1;
    const status = getStatus(q);
    const isCurrent = i === currentIndex;
    const filled = isCurrent && currentStyle === "fill";
    const cls = `mk-transition flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-meta tabular-nums md:h-11 md:w-11 ${
      filled ? STATUS_CLASS.current : STATUS_CLASS[status]
    } ${isCurrent && !filled ? "outline outline-2 outline-offset-2 outline-mk-ink-100" : ""}`;
    return (
      <button
        key={q}
        type="button"
        data-question-index={i}
        onClick={() => onSelectIndex(i)}
        className={cls}
        aria-current={isCurrent ? "step" : undefined}
        aria-label={`Question ${q}${STATUS_LABEL[status] ? `, ${STATUS_LABEL[status]}` : ""}`}
      >
        {q}
      </button>
    );
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mobile = window.matchMedia("(max-width: 767px)").matches;
    const root = mobile ? mobileScrollRef.current : desktopScrollRef.current;
    if (!root || (!mobile && !scrollable)) return;
    const el = root.querySelector<HTMLElement>(
      `[data-question-index="${currentIndex}"]`,
    );
    el?.scrollIntoView({
      inline: "center",
      block: mobile ? "nearest" : "center",
      behavior: "smooth",
    });
  }, [currentIndex, scrollable]);

  return (
    <div className="w-full min-w-0">
      <div className="md:hidden">
        <div
          ref={mobileScrollRef}
          className="overflow-x-auto overscroll-x-contain px-4 py-2 [scrollbar-width:none]"
        >
          <div className="flex w-max items-center gap-2 py-1">
            {questionButtons}
          </div>
        </div>
      </div>
      <div className="hidden md:block">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-meta text-mk-ink-60">Questions</h2>
          {countLabel ? (
            <span className="text-meta tabular-nums">{countLabel}</span>
          ) : null}
        </div>
        <div
          ref={desktopScrollRef}
          className={
            scrollable
              ? `-mx-[5px] overflow-y-auto [scrollbar-gutter:stable] ${maxHeightClassName}`
              : "-mx-[5px]"
          }
        >
          <div className="grid grid-cols-4 justify-items-center gap-2 p-[5px]">
            {questionButtons}
          </div>
        </div>
        {legend ? (
          <div className="mt-4">
            <StatusLegend items={legend} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
