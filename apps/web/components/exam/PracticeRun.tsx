"use client";

import type { Exam } from "@/lib/types";
import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { pointsForQuestionNumber } from "@/lib/scoring";
import { usePracticeAnswersStore } from "@/lib/practice-answers-store";
import { PracticeLayout } from "./PracticeLayout";
import type { QuestionStatus } from "./QuestionSidebar";

export function PracticeRun({ exam }: { exam: Exam }) {
  const router = useRouter();
  const clearPracticeProgress = usePracticeAnswersStore((s) => s.clear);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});

  const question = exam.questions[index];
  const total = exam.question_count;
  const selected = answers[question.number] ?? null;
  const revealed = selected !== null;
  const correctLabel = exam.answer_key[String(question.number)] ?? "";

  const pick = (label: string) => {
    if (revealed) return;
    setAnswers((a) => ({ ...a, [question.number]: label }));
  };

  const getStatus = useCallback(
    (q: number): QuestionStatus => {
      const sel = answers[q];
      if (!sel) return "empty";
      return sel === exam.answer_key[String(q)] ? "correct" : "wrong";
    },
    [answers, exam.answer_key],
  );

  const rightFirstTime = useMemo(
    () =>
      Object.entries(answers).filter(
        ([q, label]) => exam.answer_key[q] === label,
      ).length,
    [answers, exam.answer_key],
  );

  return (
    <PracticeLayout
      backHref="/practice"
      position={index + 1}
      total={total}
      rightFirstTime={rightFirstTime}
      getStatus={getStatus}
      onSelectIndex={setIndex}
      onGoToQuestion={(n) => setIndex(n - 1)}
      examId={exam.exam_id}
      question={question}
      assets={exam.assets}
      selectedLabel={selected}
      onPick={pick}
      correctLabel={correctLabel}
      points={
        question.points ??
        pointsForQuestionNumber(question.number, exam.scoring_rules)
      }
      onPrev={() => setIndex((i) => Math.max(0, i - 1))}
      onNext={() => setIndex((i) => Math.min(total - 1, i + 1))}
      canNext={index < total - 1 && revealed}
      onExitKeep={() => router.push("/practice")}
      onExitClear={() => {
        clearPracticeProgress();
        router.push("/practice");
      }}
    />
  );
}
