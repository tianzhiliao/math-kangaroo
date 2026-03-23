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
  const remainingPercent = Math.round((secondsLeft / durationSec) * 100);

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
  const footerButtonBase =
    "tap-target inline-flex min-h-[50px] w-full items-center justify-center rounded-2xl px-5 py-3 text-base font-semibold transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-white active:translate-y-0 disabled:pointer-events-none disabled:translate-y-0 disabled:shadow-none disabled:opacity-45";
  const footerButtonNeutral =
    `${footerButtonBase} bg-slate-200 text-slate-800 shadow-sm hover:bg-slate-300 focus-visible:ring-slate-400`;
  const footerButtonSubmit =
    `${footerButtonBase} bg-emerald-500 text-white shadow-sm hover:bg-emerald-600 focus-visible:ring-emerald-500`;
  const footerButtonExit =
    `${footerButtonBase} bg-rose-100 text-rose-800 shadow-sm hover:bg-rose-200 focus-visible:ring-rose-400`;
  const footerButtonBack =
    `${footerButtonBase} bg-blue-500 text-white shadow-sm hover:bg-blue-600 focus-visible:ring-blue-500`;

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
        <div className="flex flex-col gap-3">
          <Link
            href="/exam"
            className="tap-target inline-flex min-h-[44px] w-full items-center justify-center rounded-xl bg-slate-200 px-4 py-2.5 text-sm font-bold text-slate-800 transition hover:bg-slate-300"
          >
            Back to exams
          </Link>
          <div
            className="group rounded-xl bg-sky-100 px-3 py-2.5 shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
            aria-live="polite"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-[11px] font-bold uppercase tracking-wide text-sky-800/80">
                Time left
              </p>
              <p className="pointer-events-none select-none text-xs font-black tabular-nums text-sky-950 opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
                {submitted ? "—" : formatTime(secondsLeft)}
              </p>
            </div>
            <div
              className="mt-2 h-2 rounded-full bg-sky-200/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 focus-visible:ring-offset-sky-100"
              role="progressbar"
              aria-label="Exam time remaining"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={remainingPercent}
              tabIndex={0}
            >
              <div
                className="h-full rounded-full bg-sky-500 transition-[width] duration-700 ease-linear"
                style={{ width: `${remainingPercent}%` }}
              />
            </div>
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
          <div className="mx-auto grid w-full max-w-5xl grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
            <button
              type="button"
              onClick={goPrev}
              disabled={index === 0}
              className={`${footerButtonNeutral} order-1 md:order-1`}
            >
              Previous
            </button>
            <button
              type="button"
              onClick={goNext}
              disabled={index >= total - 1}
              className={`${footerButtonNeutral} order-2 md:order-4`}
            >
              Next
            </button>
            {!submitted ? (
              <>
                <button
                  type="button"
                  onClick={confirmSubmit}
                  className={`${footerButtonSubmit} order-3 font-bold md:order-2`}
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
                  className={`${footerButtonExit} order-4 md:order-3`}
                >
                  Exit exam
                </Link>
              </>
            ) : (
              <Link
                href="/exam"
                className={`${footerButtonBack} order-3 col-span-2 md:order-2 md:col-span-2`}
              >
                Back to exams
              </Link>
            )}
          </div>
        </footer>
      </main>
    </div>
  );
}
