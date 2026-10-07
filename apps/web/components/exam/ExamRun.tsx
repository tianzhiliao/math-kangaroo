"use client";

import { GeneratedQuestionSection } from "@/components/question/GeneratedQuestionSection";
import { QuestionCard } from "@/components/question/QuestionCard";
import { AppHeader } from "@/components/ui/AppHeader";
import { Button, ButtonLink } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import type { Exam } from "@/lib/types";
import {
  computeExamScore,
  computeTierBreakdown,
  pointsForQuestionNumber,
} from "@/lib/scoring";
import { seriesFor } from "@/lib/series";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { OutcomePill } from "./FeedbackPill";
import { QuestionSidebar, type QuestionStatus } from "./QuestionSidebar";
import { ScoreCard } from "./ScoreCard";
import { SessionFooterNav, SessionLayout } from "./SessionLayout";
import { EXAM_LEGEND, RESULT_LEGEND } from "./StatusLegend";
import { Timer } from "./Timer";

type DialogKind = "submit" | "leave" | null;

export function ExamRun({ exam }: { exam: Exam }) {
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [dialog, setDialog] = useState<DialogKind>(null);

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

  const question = exam.questions[index];
  const total = exam.question_count;
  const selected = answers[question.number] ?? null;
  const series = seriesFor(exam.level, exam.family);

  const scoreResult = useMemo(
    () => computeExamScore(exam, answers),
    [exam, answers],
  );

  const isMistake = useCallback(
    (questionNumber: number) =>
      scoreResult.perQuestion[questionNumber]?.correct === false,
    [scoreResult.perQuestion],
  );

  const finishExam = useCallback(() => {
    setDialog(null);
    setSubmitted(true);
    const firstMistake = exam.questions.findIndex((q) => isMistake(q.number));
    setIndex(firstMistake >= 0 ? firstMistake : 0);
  }, [exam.questions, isMistake]);

  useEffect(() => {
    if (!submitted && secondsLeft === 0) finishExam();
  }, [secondsLeft, submitted, finishExam]);

  const restart = () => {
    setAnswers({});
    setSubmitted(false);
    setSecondsLeft(durationSec);
    setIndex(0);
  };

  const setAnswer = useCallback(
    (label: string) => {
      if (submitted) return;
      setAnswers((a) => ({ ...a, [question.number]: label }));
    },
    [question.number, submitted],
  );

  const getStatus = useCallback(
    (q: number): QuestionStatus => {
      if (submitted) {
        const p = scoreResult.perQuestion[q];
        if (!p?.selected) return "skipped";
        return p.correct ? "correct" : "wrong";
      }
      return answers[q] ? "answered" : "empty";
    },
    [answers, scoreResult.perQuestion, submitted],
  );

  const answeredCount = Object.values(answers).filter(Boolean).length;
  const counts = useMemo(() => {
    let right = 0;
    let wrong = 0;
    for (const p of Object.values(scoreResult.perQuestion)) {
      if (p.correct === true) right += 1;
      else if (p.correct === false) wrong += 1;
    }
    return { right, wrong, skipped: total - right - wrong };
  }, [scoreResult.perQuestion, total]);
  const tiers = useMemo(
    () => computeTierBreakdown(exam, answers),
    [exam, answers],
  );

  const nextMistakeIndex = useMemo(() => {
    if (!submitted) return -1;
    for (let i = index + 1; i < exam.questions.length; i++) {
      if (isMistake(exam.questions[i].number)) return i;
    }
    return -1;
  }, [exam.questions, index, isMistake, submitted]);

  const goPrev = () => setIndex((i) => Math.max(0, i - 1));
  const goNext = () => setIndex((i) => Math.min(total - 1, i + 1));
  const isLast = index >= total - 1;

  const correctLabel = exam.answer_key[String(question.number)] ?? "";
  const points =
    question.points ??
    pointsForQuestionNumber(question.number, exam.scoring_rules);
  const minutesUsed = Math.max(
    1,
    Math.round((durationSec - secondsLeft) / 60),
  );

  let outcomeNote: React.ReactNode = null;
  if (submitted) {
    const p = scoreResult.perQuestion[question.number];
    outcomeNote = !p?.selected ? (
      <OutcomePill tone="neutral" size="sm">
        You skipped this one—the right answer is {correctLabel}. 0 points
      </OutcomePill>
    ) : p.correct ? (
      <OutcomePill tone="right" size="sm">
        You chose {p.selected}—that’s right. +{points} points
      </OutcomePill>
    ) : (
      <OutcomePill tone="wrong" size="sm">
        You chose {p.selected}—the right answer is {correctLabel}. −1 point
      </OutcomePill>
    );
  }

  const scoreCard = (
    <ScoreCard
      score={scoreResult.score}
      maxScore={scoreResult.maxScore}
      tiers={tiers}
      right={counts.right}
      wrong={counts.wrong}
      skipped={counts.skipped}
    />
  );

  const header = submitted ? (
    <AppHeader
      back={{ href: "/exam", label: "Back to papers" }}
      meta={`Exam · Submitted · ${minutesUsed} min`}
      title={`${series.name} ${exam.year}`}
      rightBelowOnMobile
      right={
        <>
          <Button variant="secondary" size="sm" onClick={restart}>
            Try this paper again
          </Button>
          <ButtonLink href="/exam" size="sm">
            Choose another paper
          </ButtonLink>
        </>
      }
    />
  ) : (
    <AppHeader
      back={{ onClick: () => setDialog("leave"), label: "Leave exam" }}
      meta={`Exam · ${series.name}`}
      title={`${exam.year} paper`}
      rightBelowOnMobile
      right={
        <>
          <Timer secondsLeft={secondsLeft} durationSec={durationSec} />
          <Button size="sm" onClick={() => setDialog("submit")}>
            Submit exam
          </Button>
        </>
      }
    />
  );

  const footer = (
    <SessionFooterNav
      previous={
        <Button variant="secondary" onClick={goPrev} disabled={index === 0}>
          Previous
        </Button>
      }
      center={
        submitted ? (
          nextMistakeIndex >= 0 ? (
            <button
              type="button"
              onClick={() => setIndex(nextMistakeIndex)}
              className="mk-transition-fast min-h-[44px] px-2 text-meta text-mk-ink-100 underline underline-offset-4 hover:text-mk-ink-60"
            >
              Next mistake: question {exam.questions[nextMistakeIndex].number}
            </button>
          ) : null
        ) : (
          `${index + 1} of ${total}`
        )
      }
      next={
        !submitted && isLast ? (
          <Button onClick={() => setDialog("submit")}>Review &amp; submit</Button>
        ) : (
          <Button onClick={goNext} disabled={isLast}>
            Next
          </Button>
        )
      }
    />
  );

  return (
    <>
      <SessionLayout
        header={header}
        sidebarClassName={submitted ? "md:w-[280px]" : "md:w-[250px]"}
        sidebar={
          <>
            {submitted ? <div className="hidden md:block">{scoreCard}</div> : null}
            <QuestionSidebar
              total={total}
              currentIndex={index}
              getStatus={getStatus}
              onSelectIndex={setIndex}
              currentStyle={submitted ? "outline" : "fill"}
              countLabel={submitted ? undefined : `${answeredCount} / ${total}`}
              legend={submitted ? RESULT_LEGEND : EXAM_LEGEND}
            />
          </>
        }
        footer={footer}
      >
        {submitted ? <div className="md:hidden">{scoreCard}</div> : null}
        <QuestionCard
          examId={exam.exam_id}
          question={question}
          allAssets={exam.assets}
          selectedLabel={selected}
          onSelect={setAnswer}
          disabled={submitted}
          showOutcome={submitted}
          correctLabel={correctLabel}
          points={points}
          outcomeNote={outcomeNote}
        />
        {submitted ? (
          <GeneratedQuestionSection
            examId={exam.exam_id}
            questionId={question.id}
          />
        ) : null}
      </SessionLayout>

      <ConfirmDialog
        open={dialog === "submit"}
        title="Submit your exam?"
        description={`You answered ${answeredCount} of ${total}. After you submit, answers can’t be changed.`}
        onCancel={() => setDialog(null)}
        actions={[
          { label: "Submit exam", variant: "primary", onClick: finishExam },
          {
            label: "Keep working",
            variant: "secondary",
            onClick: () => setDialog(null),
            initialFocus: true,
          },
        ]}
      />
      <ConfirmDialog
        open={dialog === "leave"}
        title="Leave this exam?"
        description="Answers you have not submitted will be lost."
        onCancel={() => setDialog(null)}
        actions={[
          {
            label: "Stay",
            variant: "primary",
            onClick: () => setDialog(null),
            initialFocus: true,
          },
          {
            label: "Leave exam",
            variant: "danger-soft",
            onClick: () => router.push("/exam"),
          },
        ]}
      />
    </>
  );
}
