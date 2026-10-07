"use client";

import { GeneratedQuestionSection } from "@/components/question/GeneratedQuestionSection";
import { QuestionCard } from "@/components/question/QuestionCard";
import { AppHeader } from "@/components/ui/AppHeader";
import { Button } from "@/components/ui/Button";
import type { AssetRecord, Question } from "@/lib/types";
import { useId, useState } from "react";
import { FeedbackPill } from "./FeedbackPill";
import { PracticeExitDialog } from "./PracticeExitDialog";
import { PracticeExplanationPanel } from "./PracticeExplanationPanel";
import { QuestionSidebar, type QuestionStatus } from "./QuestionSidebar";
import { SessionFooterNav, SessionLayout } from "./SessionLayout";
import { PRACTICE_LEGEND } from "./StatusLegend";

function GoToQuestion({
  total,
  onGo,
}: {
  total: number;
  onGo: (oneBased: number) => void;
}) {
  const id = useId();
  const [value, setValue] = useState("");
  const [error, setError] = useState(false);

  const submit = () => {
    const n = Number(value);
    if (!Number.isInteger(n) || n < 1 || n > total) {
      setError(true);
      return;
    }
    setError(false);
    setValue("");
    onGo(n);
  };

  return (
    <div className="hidden md:block">
      <label htmlFor={id} className="text-meta text-mk-ink-60">
        Go to question
      </label>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        min={1}
        max={total}
        value={value}
        placeholder={`1 to ${total}`}
        aria-invalid={error || undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(e) => {
          setValue(e.target.value);
          if (error) setError(false);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            submit();
          }
        }}
        className={`mk-transition mt-2 h-11 w-full rounded-md border bg-mk-bg px-3.5 text-[16px] tabular-nums placeholder:text-mk-ink-44 ${
          error ? "border-mk-wrong-strong" : "border-mk-ink-12 hover:border-mk-ink-44"
        } [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none`}
      />
      {error ? (
        <p id={`${id}-error`} className="mt-1.5 text-caption text-mk-wrong-fg">
          Enter a number from 1 to {total}
        </p>
      ) : null}
    </div>
  );
}

/**
 * Shared practice screen for the question bank and single-paper practice
 * (plan-c.md §6.5). Callers own the data and navigation.
 */
export function PracticeLayout({
  backHref,
  position,
  total,
  rightFirstTime,
  getStatus,
  onSelectIndex,
  onGoToQuestion,
  examId,
  question,
  assets,
  selectedLabel,
  onPick,
  correctLabel,
  metaLabel,
  points,
  onPrev,
  onNext,
  canNext,
  onExitKeep,
  onExitClear,
}: {
  backHref: string;
  /** 1-based position of the current question. */
  position: number;
  total: number;
  rightFirstTime: number;
  getStatus: (q: number) => QuestionStatus;
  onSelectIndex: (zeroBased: number) => void;
  onGoToQuestion: (oneBased: number) => void;
  examId: string;
  question: Question;
  assets: AssetRecord[];
  selectedLabel: string | null;
  onPick: (label: string) => void;
  correctLabel: string;
  metaLabel?: string;
  points?: number;
  onPrev: () => void;
  onNext: () => void;
  canNext: boolean;
  onExitKeep: () => void;
  onExitClear: () => void;
}) {
  const [showExitDialog, setShowExitDialog] = useState(false);
  const revealed = selectedLabel !== null;
  const isCorrect = revealed && selectedLabel === correctLabel;
  const correctText = question.choices.find(
    (c) => c.label === correctLabel,
  )?.text;

  const feedback = revealed ? (
    <FeedbackPill
      isCorrect={isCorrect}
      correctLabel={correctLabel}
      correctText={correctText}
    />
  ) : null;

  return (
    <>
      <SessionLayout
        header={
          <AppHeader
            back={{ href: backHref, label: "Back" }}
            meta={`Practice · ${rightFirstTime} right first time`}
            title={`Question ${position} of ${total}`}
            right={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowExitDialog(true)}
                className="max-md:min-h-[40px] max-md:px-4"
              >
                <span className="md:hidden">End</span>
                <span className="hidden md:inline">End practice</span>
              </Button>
            }
          />
        }
        sidebarClassName="md:w-[280px]"
        sidebar={
          <>
            <GoToQuestion total={total} onGo={onGoToQuestion} />
            <QuestionSidebar
              total={total}
              currentIndex={position - 1}
              getStatus={getStatus}
              onSelectIndex={onSelectIndex}
              legend={PRACTICE_LEGEND}
              scrollable
              maxHeightClassName="md:max-h-[calc(100dvh-64px-220px)]"
            />
          </>
        }
        footer={
          <SessionFooterNav
            top={feedback}
            previous={
              <Button
                variant="secondary"
                onClick={onPrev}
                disabled={position <= 1}
              >
                Previous
              </Button>
            }
            center={`${position} of ${total}`}
            next={
              <Button onClick={onNext} disabled={!canNext}>
                Next question
              </Button>
            }
          />
        }
      >
        <QuestionCard
          examId={examId}
          question={question}
          allAssets={assets}
          selectedLabel={selectedLabel}
          onSelect={onPick}
          disabled={revealed}
          showOutcome={revealed}
          correctLabel={correctLabel}
          metaLabel={metaLabel}
          points={points}
          displayQuestionNumber={position}
        />
        {feedback ? <div className="hidden md:block">{feedback}</div> : null}
        <PracticeExplanationPanel
          examId={examId}
          questionNumber={question.number}
          selectedLabel={selectedLabel}
          expectedCorrectLabel={correctLabel}
        />
        <GeneratedQuestionSection examId={examId} questionId={question.id} />
        {/* Keeps the last block clear of the phone footer's feedback pill. */}
        <div className="h-2 md:hidden" aria-hidden />
      </SessionLayout>
      <PracticeExitDialog
        open={showExitDialog}
        questionNumber={position}
        onCancel={() => setShowExitDialog(false)}
        onKeep={() => {
          setShowExitDialog(false);
          onExitKeep();
        }}
        onClear={() => {
          setShowExitDialog(false);
          onExitClear();
        }}
      />
    </>
  );
}
