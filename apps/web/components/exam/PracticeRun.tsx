"use client";

import { QuestionCard } from "@/components/question/QuestionCard";
import type { Exam } from "@/lib/types";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  QuestionSidebar,
  type QuestionStatus,
} from "@/components/exam/QuestionSidebar";
import { PracticeExplanationPanel } from "@/components/exam/PracticeExplanationPanel";
import { PracticeExitDialog } from "@/components/exam/PracticeExitDialog";
import { usePracticeAnswersStore } from "@/lib/practice-answers-store";

export function PracticeRun({ exam }: { exam: Exam }) {
  const router = useRouter();
  const clearPracticeProgress = usePracticeAnswersStore((s) => s.clear);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [revealed, setRevealed] = useState(false);
  const [showExitDialog, setShowExitDialog] = useState(false);

  const question = exam.questions[index];
  const total = exam.question_count;
  const selected = answers[question.number] ?? null;
  const correctLabel = exam.answer_key[String(question.number)] ?? "";

  const pick = (label: string) => {
    if (revealed) return;
    setAnswers((a) => ({ ...a, [question.number]: label }));
    setRevealed(true);
  };

  const goNext = () => {
    if (index >= total - 1 || !revealed) return;
    const newIndex = index + 1;
    setIndex(newIndex);
    const qn = exam.questions[newIndex].number;
    setRevealed(!!answers[qn]);
  };

  const goPrev = () => {
    if (index <= 0) return;
    const newIndex = index - 1;
    setIndex(newIndex);
    const qn = exam.questions[newIndex].number;
    setRevealed(!!answers[qn]);
  };

  const getStatus = useCallback(
    (q: number): QuestionStatus => {
      const sel = answers[q];
      if (!sel) return "empty";
      const ok = exam.answer_key[String(q)];
      if (sel === ok) return "correct";
      return "wrong";
    },
    [answers, exam.answer_key],
  );

  const jumpTo = (i: number) => {
    setIndex(i);
    const qn = exam.questions[i].number;
    setRevealed(!!answers[qn]);
  };

  const showOutcome = revealed;
  const isCorrect = revealed && selected === correctLabel;

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[var(--background)] md:flex-row">
      <aside className="flex shrink-0 flex-col gap-6 border-b border-slate-200 bg-white/90 p-4 md:w-60 md:border-b-0 md:border-r">
        <div className="flex flex-col gap-4">
          <Link
            href="/practice"
            className="tap-target inline-flex w-fit items-center justify-center rounded-xl bg-slate-200 px-4 text-sm font-bold text-slate-800"
          >
            Back to practice
          </Link>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-center shadow-inner">
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-900/80">
              Practice mode
            </p>
            <p className="mt-1 text-sm font-semibold text-emerald-950">
              See feedback after each answer.
            </p>
          </div>
        </div>

        <QuestionSidebar
          total={total}
          currentIndex={index}
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
            showOutcome={showOutcome}
            correctLabel={correctLabel}
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
          <PracticeExplanationPanel
            examId={exam.exam_id}
            questionNumber={question.number}
            selectedLabel={selected}
            expectedCorrectLabel={correctLabel}
          />
        </div>

        <footer className="sticky bottom-0 border-t border-slate-200 bg-white/95 px-3 py-4 backdrop-blur sm:px-4 sm:py-5">
          <div className="mx-auto flex w-full max-w-4xl flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-center sm:gap-4">
            <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-1 sm:justify-center sm:gap-4">
              <button
                type="button"
                onClick={goPrev}
                disabled={index === 0}
                className="tap-target min-h-[48px] rounded-2xl bg-slate-200 px-4 text-base font-bold text-slate-800 disabled:opacity-40 sm:min-w-[7.5rem] sm:px-5"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={goNext}
                disabled={index >= total - 1 || !revealed}
                className="tap-target min-h-[48px] rounded-2xl bg-blue-500 px-4 text-base font-black text-white shadow-md disabled:opacity-40 sm:min-w-[7.5rem] sm:px-6"
              >
                Next
              </button>
            </div>
            <button
              type="button"
              onClick={() => setShowExitDialog(true)}
              className="tap-target flex min-h-[48px] w-full items-center justify-center gap-2 rounded-2xl bg-rose-100 px-5 text-base font-bold text-rose-800 sm:w-auto sm:shrink-0 sm:px-6"
            >
              <span aria-hidden>×</span>
              End practice
            </button>
          </div>
        </footer>
      </main>
      <PracticeExitDialog
        open={showExitDialog}
        onCancel={() => setShowExitDialog(false)}
        onKeep={() => {
          setShowExitDialog(false);
          router.push("/practice");
        }}
        onClear={() => {
          clearPracticeProgress();
          setShowExitDialog(false);
          router.push("/practice");
        }}
      />
    </div>
  );
}
