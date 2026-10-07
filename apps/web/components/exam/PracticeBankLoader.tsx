"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { PageState } from "@/components/ui/PageState";
import { usePracticeAnswersStore } from "@/lib/practice-answers-store";
import { useExam, usePracticeBank } from "@/lib/queries";
import { pointsForQuestionNumber } from "@/lib/scoring";
import { seriesFor } from "@/lib/series";
import { PracticeLayout } from "./PracticeLayout";
import type { QuestionStatus } from "./QuestionSidebar";

export function PracticeBankLoader() {
  const params = useParams();
  const router = useRouter();
  const raw = params.globalIndex;
  const globalOneBased =
    typeof raw === "string" ? Number.parseInt(raw, 10) : Number.NaN;

  const { data: bank, isPending: bankPending } = usePracticeBank();

  const total = bank?.total ?? 0;
  const entry =
    bank && globalOneBased >= 1 && globalOneBased <= total
      ? bank.entries[globalOneBased - 1]
      : undefined;

  const {
    data: exam,
    isPending: examPending,
    isError: examError,
    refetch: refetchExam,
  } = useExam(entry?.exam_id);

  const question = useMemo(() => {
    if (!exam || !entry) return undefined;
    return exam.questions.find((q) => q.number === entry.question_number);
  }, [exam, entry]);

  const answers = usePracticeAnswersStore((s) => s.answers);
  const setAnswer = usePracticeAnswersStore((s) => s.setAnswer);
  const setLastVisitedQuestion = usePracticeAnswersStore(
    (s) => s.setLastVisitedQuestion,
  );
  const clearPracticeProgress = usePracticeAnswersStore((s) => s.clear);

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

  const goTo = (oneBased: number) => router.push(`/practice/q/${oneBased}`);

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

  const rightFirstTime = useMemo(() => {
    if (!bank) return 0;
    let n = 0;
    for (const [k, label] of Object.entries(answers)) {
      if (bank.entries[Number(k) - 1]?.correct_label === label) n += 1;
    }
    return n;
  }, [answers, bank]);

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

  if (bankPending) return <PageState message="Loading question bank…" />;
  if (!bank?.entries.length) {
    return (
      <PageState
        title="No questions yet"
        message="They appear here once added."
        actions={
          <ButtonLink href="/" variant="secondary">
            Back to home
          </ButtonLink>
        }
      />
    );
  }

  if (
    Number.isNaN(globalOneBased) ||
    globalOneBased < 1 ||
    globalOneBased > total
  ) {
    return (
      <PageState
        title={`There is no question ${Number.isNaN(globalOneBased) ? raw : globalOneBased}`}
        message={`Practice has questions 1 to ${total}.`}
        actions={<ButtonLink href="/practice/q/1">Go to question 1</ButtonLink>}
      />
    );
  }

  if (examError) {
    return (
      <PageState
        title="Could not load this question"
        message="Check the connection and try again."
        actions={
          <>
            <Button onClick={() => void refetchExam()}>Try again</Button>
            <ButtonLink href="/" variant="secondary">
              Back to home
            </ButtonLink>
          </>
        }
      />
    );
  }

  if (examPending || !exam || !question) {
    return <PageState message="Loading…" />;
  }

  const series = seriesFor(exam.level, exam.family);
  const points =
    question.points ??
    pointsForQuestionNumber(question.number, exam.scoring_rules);

  return (
    <PracticeLayout
      backHref="/"
      position={globalOneBased}
      total={total}
      rightFirstTime={rightFirstTime}
      getStatus={getStatus}
      onSelectIndex={(i) => goTo(i + 1)}
      onGoToQuestion={goTo}
      examId={exam.exam_id}
      question={question}
      assets={exam.assets}
      selectedLabel={selected}
      onPick={pick}
      correctLabel={correctLabel}
      metaLabel={`${series.name} ${exam.year} · Question ${question.number} · ${points} points`}
      onPrev={() => goTo(globalOneBased - 1)}
      onNext={() => goTo(globalOneBased + 1)}
      canNext={globalOneBased < total}
      onExitKeep={() => router.push("/")}
      onExitClear={() => {
        clearPracticeProgress();
        router.push("/");
      }}
    />
  );
}
