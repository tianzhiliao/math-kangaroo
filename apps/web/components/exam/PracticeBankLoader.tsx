"use client";

import { useQuery } from "@tanstack/react-query";
import type { Exam, PracticeBankResponse } from "@/lib/types";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo } from "react";
import { QuestionCard } from "@/components/question/QuestionCard";
import { usePracticeAnswersStore } from "@/lib/practice-answers-store";
import {
  QuestionSidebar,
  type QuestionStatus,
} from "@/components/exam/QuestionSidebar";

function Loading() {
  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-3 text-slate-600">
      <span
        className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent"
        aria-hidden
      />
      <span className="text-lg font-medium">Loading…</span>
    </div>
  );
}

export function PracticeBankLoader() {
  const params = useParams();
  const router = useRouter();
  const raw = params.globalIndex;
  const globalOneBased =
    typeof raw === "string" ? Number.parseInt(raw, 10) : Number.NaN;

  const { data: bank, isPending: bankPending } = useQuery({
    queryKey: ["practice-bank"],
    queryFn: async () => {
      const r = await fetch("/api/practice-bank");
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<PracticeBankResponse>;
    },
  });

  const total = bank?.total ?? 0;
  const entry =
    bank && globalOneBased >= 1 && globalOneBased <= total
      ? bank.entries[globalOneBased - 1]
      : undefined;

  const { data: exam, isPending: examPending } = useQuery({
    queryKey: ["exam", entry?.exam_id],
    queryFn: async () => {
      const r = await fetch(
        `/api/exams/${encodeURIComponent(entry!.exam_id)}`,
      );
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<Exam>;
    },
    enabled: !!entry,
  });

  const question = useMemo(() => {
    if (!exam || !entry) return undefined;
    return exam.questions.find((q) => q.number === entry.question_number);
  }, [exam, entry]);

  const answers = usePracticeAnswersStore((s) => s.answers);
  const setAnswer = usePracticeAnswersStore((s) => s.setAnswer);
  const setLastVisitedQuestion = usePracticeAnswersStore(
    (s) => s.setLastVisitedQuestion,
  );

  const selected =
    globalOneBased >= 1 && answers[globalOneBased]
      ? answers[globalOneBased]
      : null;
  const revealed = selected !== null;
  const correctLabel = entry?.correct_label ?? "";

  const pick = (label: string) => {
    if (revealed) return;
    setAnswer(globalOneBased, label);
  };

  const goNext = () => {
    if (globalOneBased >= total) return;
    router.push(`/practice/q/${globalOneBased + 1}`);
  };

  const goPrev = () => {
    if (globalOneBased <= 1) return;
    router.push(`/practice/q/${globalOneBased - 1}`);
  };

  const jumpTo = (zeroBasedIndex: number) => {
    router.push(`/practice/q/${zeroBasedIndex + 1}`);
  };

  const getStatus = useCallback(
    (q: number): QuestionStatus => {
      const sel = answers[q] ?? null;
      if (!sel) return "empty";
      const e = bank?.entries[q - 1];
      if (!e) return "empty";
      return sel === e.correct_label ? "correct" : "wrong";
    },
    [answers, bank],
  );

  const isCorrect = revealed && selected === correctLabel;
  const footerButtonBase =
    "tap-target inline-flex min-h-[50px] w-full items-center justify-center rounded-2xl px-5 py-3 text-base font-semibold transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-white active:translate-y-0 disabled:pointer-events-none disabled:translate-y-0 disabled:shadow-none disabled:opacity-45";
  const footerButtonNeutral =
    `${footerButtonBase} bg-slate-200 text-slate-800 shadow-sm hover:bg-slate-300 focus-visible:ring-slate-400`;
  const footerButtonPrimary =
    `${footerButtonBase} bg-blue-500 text-white shadow-sm hover:bg-blue-600 focus-visible:ring-blue-500`;
  const footerButtonDanger =
    `${footerButtonBase} gap-2 bg-rose-100 text-rose-800 shadow-sm hover:bg-rose-200 focus-visible:ring-rose-400`;

  useEffect(() => {
    if (
      Number.isNaN(globalOneBased) ||
      globalOneBased < 1 ||
      globalOneBased > total
    ) {
      return;
    }
    setLastVisitedQuestion(globalOneBased);
  }, [globalOneBased, total, setLastVisitedQuestion]);

  if (bankPending) return <Loading />;
  if (!bank?.entries.length) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-600">No questions in the bank yet.</p>
        <Link href="/" className="mt-4 inline-block font-bold text-emerald-600">
          Back to Home
        </Link>
      </div>
    );
  }

  if (
    Number.isNaN(globalOneBased) ||
    globalOneBased < 1 ||
    globalOneBased > total
  ) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-600">Invalid question number.</p>
        <Link
          href="/practice/q/1"
          className="mt-4 inline-block font-bold text-emerald-600"
        >
          Go to first question
        </Link>
      </div>
    );
  }

  if (examPending || !exam || !question) {
    return <Loading />;
  }

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[var(--background)] md:flex-row">
      <aside className="flex max-h-[min(48vh,420px)] shrink-0 flex-col gap-4 overflow-hidden border-b border-slate-200 bg-white/90 p-4 md:max-h-[calc(100dvh-1rem)] md:w-64 md:border-b-0 md:border-r">
        <div className="flex flex-col gap-2.5">
          <Link
            href="/"
            className="tap-target inline-flex min-h-[44px] w-full items-center justify-center rounded-xl bg-slate-200 px-4 py-2.5 text-sm font-bold text-slate-800 transition hover:bg-slate-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
          >
            Back to Home
          </Link>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-center shadow-inner">
            <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-900/75">
              Math Kangaroo · Practice
            </p>
            <p className="mt-1 text-sm font-bold text-emerald-950">
              Question {globalOneBased} of {total}
            </p>
          </div>
        </div>

        <QuestionSidebar
          total={total}
          currentIndex={globalOneBased - 1}
          getStatus={getStatus}
          onSelectIndex={jumpTo}
          scrollable
          maxHeightClassName="max-h-[min(30vh,260px)] md:max-h-[calc(100dvh-14rem)]"
        />
      </aside>

      <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex min-h-0 flex-1 flex-col items-stretch justify-start overflow-y-auto px-2 py-1 sm:px-3 sm:py-2">
          <QuestionCard
            examId={exam.exam_id}
            question={question}
            allAssets={exam.assets}
            selectedLabel={selected}
            onSelect={pick}
            disabled={revealed}
            showOutcome={revealed}
            correctLabel={correctLabel}
            displayQuestionNumber={globalOneBased}
          />
          {revealed ? (
            <p
              className="mt-2 text-center text-lg font-bold text-slate-800 sm:text-xl"
              aria-live="polite"
            >
              {isCorrect ? (
                <span>
                  <span className="text-emerald-600" aria-hidden>
                    ✓{" "}
                  </span>
                  Correct
                </span>
              ) : (
                <span>
                  <span className="text-red-500" aria-hidden>
                    ✗{" "}
                  </span>
                  Not quite — check the answer
                </span>
              )}
            </p>
          ) : null}
        </div>

        <footer className="sticky bottom-0 border-t border-slate-200 bg-white/95 px-3 py-4 backdrop-blur sm:px-4 sm:py-5">
          <div className="mx-auto grid w-full max-w-5xl grid-cols-2 gap-3 md:grid-cols-3 md:gap-4">
            <button
              type="button"
              onClick={goPrev}
              disabled={globalOneBased <= 1}
              className={`${footerButtonNeutral} order-1`}
            >
              Previous
            </button>
            <button
              type="button"
              onClick={goNext}
              disabled={globalOneBased >= total}
              className={`${footerButtonPrimary} order-2 font-bold`}
            >
              Next
            </button>
            <Link
              href="/"
              onClick={(e) => {
                if (
                  !window.confirm(
                    "Leave practice? Your progress on this page is not saved.",
                  )
                ) {
                  e.preventDefault();
                }
              }}
              className={`${footerButtonDanger} order-3 col-span-2 md:col-span-1`}
            >
              End practice
            </Link>
          </div>
        </footer>
      </main>
    </div>
  );
}
