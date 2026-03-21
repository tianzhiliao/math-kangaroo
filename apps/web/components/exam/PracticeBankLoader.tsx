"use client";

import { useQuery } from "@tanstack/react-query";
import type { Exam, PracticeBankResponse } from "@/lib/types";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useMemo } from "react";
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
    if (globalOneBased >= total || !revealed) return;
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
          href="/practice"
          className="mt-4 inline-block font-bold text-emerald-600"
        >
          Back to question list
        </Link>
      </div>
    );
  }

  if (examPending || !exam || !question) {
    return <Loading />;
  }

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[var(--background)] md:flex-row">
      <aside className="flex max-h-[min(40vh,320px)] shrink-0 flex-col gap-4 overflow-y-auto border-b border-slate-200 bg-white/90 p-4 md:max-h-none md:w-64 md:border-b-0 md:border-r">
        <div className="flex flex-col gap-3">
          <Link
            href="/practice"
            className="tap-target inline-flex w-fit items-center justify-center rounded-xl bg-slate-200 px-4 text-sm font-bold text-slate-800"
          >
            All questions
          </Link>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-center shadow-inner">
            <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-900/80">
              Math Kangaroo · Practice
            </p>
            <p className="mt-0.5 text-xs font-semibold text-emerald-950">
              Question {globalOneBased} of {total}
            </p>
          </div>
        </div>

        <QuestionSidebar
          total={total}
          currentIndex={globalOneBased - 1}
          getStatus={getStatus}
          onSelectIndex={jumpTo}
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
          <div className="mx-auto flex w-full max-w-4xl flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-center sm:gap-4">
            <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-1 sm:justify-center sm:gap-4">
              <button
                type="button"
                onClick={goPrev}
                disabled={globalOneBased <= 1}
                className="tap-target min-h-[48px] rounded-2xl bg-slate-200 px-4 text-base font-bold text-slate-800 disabled:opacity-40 sm:min-w-[7.5rem] sm:px-5"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={goNext}
                disabled={globalOneBased >= total || !revealed}
                className="tap-target min-h-[48px] rounded-2xl bg-blue-500 px-4 text-base font-black text-white shadow-md disabled:opacity-40 sm:min-w-[7.5rem] sm:px-6"
              >
                Next
              </button>
            </div>
            <Link
              href="/practice"
              onClick={(e) => {
                if (
                  !window.confirm(
                    "Leave practice? Your progress on this page is not saved.",
                  )
                ) {
                  e.preventDefault();
                }
              }}
              className="tap-target flex min-h-[48px] w-full items-center justify-center gap-2 rounded-2xl bg-rose-100 px-5 text-base font-bold text-rose-800 sm:w-auto sm:shrink-0 sm:px-6"
            >
              <span aria-hidden>×</span>
              End practice
            </Link>
          </div>
        </footer>
      </main>
    </div>
  );
}
