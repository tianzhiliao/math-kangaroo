"use client";

import { QuestionCard } from "@/components/question/QuestionCard";
import type { Exam } from "@/lib/types";
import { computeExamScore } from "@/lib/scoring";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  QuestionSidebar,
  type QuestionStatus,
} from "@/components/exam/QuestionSidebar";

function formatTime(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function ExamRun({ exam }: { exam: Exam }) {
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const durationSec = useMemo(() => {
    const m = exam.duration_minutes ?? 45;
    return Math.max(60, m * 60);
  }, [exam.duration_minutes]);

  const [secondsLeft, setSecondsLeft] = useState(durationSec);

  useEffect(() => {
    if (submitted) return;
    const t = setInterval(() => {
      setSecondsLeft((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(t);
  }, [submitted]);

  useEffect(() => {
    if (submitted) return;
    if (secondsLeft === 0) {
      setSubmitted(true);
    }
  }, [secondsLeft, submitted]);

  const question = exam.questions[index];
  const total = exam.question_count;
  const selected = answers[question.number] ?? null;

  const scoreResult = useMemo(
    () => computeExamScore(exam, answers),
    [exam, answers],
  );

  const setAnswer = useCallback(
    (label: string) => {
      if (submitted) return;
      setAnswers((a) => ({ ...a, [question.number]: label }));
    },
    [question.number, submitted],
  );

  const getStatus = useCallback(
    (q: number): QuestionStatus => {
      const sel = answers[q] ?? null;
      if (submitted) {
        const p = scoreResult.perQuestion[q];
        if (!p?.selected) return "skipped";
        return p.correct ? "correct" : "wrong";
      }
      return sel ? "answered" : "empty";
    },
    [answers, scoreResult.perQuestion, submitted],
  );

  const goPrev = () => setIndex((i) => Math.max(0, i - 1));
  const goNext = () => setIndex((i) => Math.min(total - 1, i + 1));

  const confirmSubmit = () => {
    if (
      typeof window !== "undefined" &&
      !window.confirm(
        "Submit your exam now? You will not be able to change answers after submitting.",
      )
    ) {
      return;
    }
    setSubmitted(true);
  };

  const correctLabel = exam.answer_key[String(question.number)] ?? "";

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[var(--background)] md:flex-row">
      <aside className="flex shrink-0 flex-col gap-6 border-b border-slate-200 bg-white/90 p-4 md:w-60 md:border-b-0 md:border-r">
        <div className="flex flex-col gap-4">
          <Link
            href="/exam"
            className="tap-target inline-flex w-fit items-center justify-center rounded-xl bg-slate-200 px-4 text-sm font-bold text-slate-800"
          >
            Back to exams
          </Link>
          <div
            className="rounded-2xl bg-sky-100 px-4 py-3 text-center shadow-inner"
            aria-live="polite"
          >
            <p className="text-xs font-bold uppercase tracking-wide text-sky-800/80">
              Time left
            </p>
            <p className="mt-1 text-2xl font-black tabular-nums text-sky-950">
              {submitted ? "—" : formatTime(secondsLeft)}
            </p>
          </div>
        </div>

        <QuestionSidebar
          total={total}
          currentIndex={index}
          getStatus={getStatus}
          onSelectIndex={setIndex}
        />

        {submitted ? (
          <p className="text-center text-2xl font-black text-slate-800">
            Score: {scoreResult.score} / {scoreResult.maxScore}
          </p>
        ) : null}
      </aside>

      <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex min-h-0 flex-1 flex-col items-stretch justify-start overflow-y-auto px-2 py-1 sm:px-3 sm:py-2">
          <QuestionCard
            examId={exam.exam_id}
            question={question}
            allAssets={exam.assets}
            selectedLabel={selected}
            onSelect={setAnswer}
            disabled={submitted}
            showOutcome={submitted}
            correctLabel={correctLabel}
          />
        </div>

        <footer className="sticky bottom-0 border-t border-slate-200 bg-white/95 px-3 py-4 backdrop-blur sm:px-4 sm:py-5">
          {/* Mobile: row1 = Prev | Next, row2 = actions; Desktop: 3-column row */}
          <div className="mx-auto grid w-full max-w-4xl grid-cols-2 gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-center sm:gap-6">
            <button
              type="button"
              onClick={goPrev}
              disabled={index === 0}
              className="tap-target col-start-1 row-start-1 justify-self-stretch rounded-2xl bg-slate-200 px-4 py-3 text-base font-bold text-slate-800 disabled:opacity-40 sm:col-start-1 sm:justify-self-start sm:px-6"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={goNext}
              disabled={index >= total - 1}
              className="tap-target col-start-2 row-start-1 justify-self-stretch rounded-2xl bg-slate-200 px-4 py-3 text-base font-bold text-slate-800 disabled:opacity-40 sm:col-start-3 sm:row-start-1 sm:justify-self-end sm:px-6"
            >
              Next
            </button>
            <div className="col-span-2 row-start-2 flex flex-col gap-3 sm:col-span-1 sm:col-start-2 sm:row-start-1 sm:flex-row sm:flex-wrap sm:justify-center sm:gap-5">
              {!submitted ? (
                <>
                  <button
                    type="button"
                    onClick={confirmSubmit}
                    className="tap-target inline-flex min-h-[48px] w-full items-center justify-center rounded-2xl bg-emerald-500 px-5 py-3 text-base font-black text-white shadow-md sm:w-auto sm:min-w-0 sm:px-7"
                  >
                    Submit exam
                  </button>
                  <Link
                    href="/exam"
                    onClick={(e) => {
                      if (
                        !window.confirm(
                          "Leave this exam? You will lose any answers that are not submitted.",
                        )
                      ) {
                        e.preventDefault();
                      }
                    }}
                    className="tap-target inline-flex min-h-[48px] w-full items-center justify-center rounded-2xl bg-rose-100 px-5 py-3 text-base font-bold text-rose-800 sm:w-auto sm:px-6"
                  >
                    Exit exam
                  </Link>
                </>
              ) : (
                <Link
                  href="/exam"
                  className="tap-target flex min-h-[48px] w-full items-center justify-center rounded-2xl bg-blue-500 px-7 py-3 text-base font-bold text-white sm:w-auto"
                >
                  Back to exams
                </Link>
              )}
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
