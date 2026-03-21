"use client";

import { useEffect, useMemo, useState } from "react";

import { QuestionPalette } from "@/components/question-palette";
import { QuestionStage } from "@/components/question-stage";
import { formatDuration } from "@/lib/formatting";
import {
  createExamSession,
  getPartBreakdown,
  getRemainingSeconds,
  jumpExamQuestion,
  submitExamSession,
  toggleMarkedQuestion,
  answerExamQuestion,
} from "@/lib/session-models";
import { clearExamSession, loadExamSession, saveExamSession } from "@/lib/session-storage";
import type { ExamSession, HydratedExam } from "@/lib/types";

interface ExamExperienceProps {
  exam: HydratedExam;
}

export function ExamExperience({ exam }: ExamExperienceProps) {
  const [session, setSession] = useState<ExamSession | null>(null);
  const [startQuestionNumber, setStartQuestionNumber] = useState(exam.availableQuestionNumbers[0] ?? 1);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    const stored = loadExamSession(exam.examId);
    setSession(stored);
    setIsHydrated(true);
  }, [exam.examId]);

  useEffect(() => {
    if (!session) {
      return;
    }

    saveExamSession(session);
  }, [session]);

  const [remainingSeconds, setRemainingSeconds] = useState(exam.durationMinutes * 60);

  useEffect(() => {
    if (!session || session.status !== "in_progress") {
      setRemainingSeconds(exam.durationMinutes * 60);
      return;
    }

    const updateRemaining = () => {
      const next = getRemainingSeconds(session);
      setRemainingSeconds(next);
      if (next <= 0) {
        setSession((current) => {
          if (!current || current.status !== "in_progress") {
            return current;
          }

          return submitExamSession(current, exam, "timed_out");
        });
      }
    };

    updateRemaining();
    const timer = window.setInterval(updateRemaining, 1000);
    return () => window.clearInterval(timer);
  }, [exam, exam.durationMinutes, session]);

  const activeSession = session?.status === "in_progress" ? session : null;
  const activeQuestionNumber = activeSession?.currentQuestionNumber ?? startQuestionNumber;
  const activeQuestion = exam.questionLookup[activeQuestionNumber];
  const answeredNumbers = useMemo(
    () => Object.keys(activeSession?.answers ?? {}).map((value) => Number(value)),
    [activeSession?.answers],
  );
  const result = session?.result ?? null;
  const partBreakdown = getPartBreakdown(exam, result);

  function beginExam() {
    setSession(createExamSession(exam, startQuestionNumber));
  }

  function restartExam() {
    clearExamSession(exam.examId);
    setSession(null);
  }

  function submitCurrentExam() {
    setSession((current) => {
      if (!current || current.status !== "in_progress") {
        return current;
      }

      return submitExamSession(current, exam, "submitted");
    });
  }

  function moveQuestion(step: -1 | 1) {
    if (!activeSession) {
      return;
    }

    const currentIndex = exam.availableQuestionNumbers.indexOf(activeSession.currentQuestionNumber);
    const nextIndex = currentIndex + step;
    const nextQuestion = exam.availableQuestionNumbers[nextIndex];

    if (!nextQuestion) {
      return;
    }

    setSession(jumpExamQuestion(activeSession, nextQuestion));
  }

  if (!isHydrated) {
    return (
      <section className="panel">
        <div className="panel-inner">
          <p className="lede">Preparing your exam workspace...</p>
        </div>
      </section>
    );
  }

  if (!session || session.status === "idle") {
    return (
      <div className="split-layout">
        <section className="panel">
          <div className="panel-inner">
            <div className="eyebrow">Paper setup</div>
            <h2 className="section-title">{exam.title}</h2>
            <p className="lede">
              {exam.subtitle}. Choose where to begin, then start the paper to lock in timing and scoring.
            </p>
            <div className="summary-grid" style={{ marginTop: 24 }}>
              <div className="summary-item">
                <strong>{exam.questionCount}</strong>
                <span>questions</span>
              </div>
              <div className="summary-item">
                <strong>{formatDuration(exam.durationMinutes)}</strong>
                <span>{exam.officialDuration ? "official timing" : "family default timing"}</span>
              </div>
              <div className="summary-item">
                <strong>{exam.startingPoints}</strong>
                <span>starting points</span>
              </div>
              <div className="summary-item">
                <strong>{exam.maxScore}</strong>
                <span>maximum score</span>
              </div>
            </div>
            <div className="divider" />
            <div className="field-stack" style={{ maxWidth: 280 }}>
              <label htmlFor="start-question-select">Start from question</label>
              <select
                id="start-question-select"
                value={startQuestionNumber}
                onChange={(event) => setStartQuestionNumber(Number(event.target.value))}
              >
                {exam.availableQuestionNumbers.map((questionNumber) => (
                  <option key={questionNumber} value={questionNumber}>
                    Question {questionNumber}
                  </option>
                ))}
              </select>
            </div>
            <div className="pill-row" style={{ marginTop: 18 }}>
              <span className="stat-pill">{exam.rulesSummary}</span>
              <span className="stat-pill">{exam.penaltySummary}</span>
            </div>
            {!exam.officialDuration ? (
              <div className="status-banner" style={{ marginTop: 18 }}>
                <p>This paper did not ship with an official duration in the dataset, so a family-level default is used.</p>
              </div>
            ) : null}
            <div className="action-row" style={{ marginTop: 24 }}>
              <button className="primary-button" type="button" onClick={beginExam}>
                Start timed paper
              </button>
            </div>
          </div>
        </section>
        <aside className="sidebar-column">
          <section className="panel">
            <div className="panel-inner">
              <div className="eyebrow">How it works</div>
              <div className="field-stack">
                <div className="status-banner">
                  <p>Your answers save locally in this browser while the exam is in progress.</p>
                </div>
                <div className="status-banner">
                  <p>You may jump to any question, flag it, and return before submission.</p>
                </div>
                <div className="status-banner">
                  <p>Correctness stays hidden until you submit or the timer runs out.</p>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </div>
    );
  }

  if (session.status === "submitted" || session.status === "timed_out") {
    const questionStatusMap = new Map(result?.questionResults.map((entry) => [entry.questionNumber, entry]) ?? []);

    return (
      <section className="hero-grid">
        <div className="panel">
          <div className="panel-inner">
            <div className="eyebrow">{session.status === "timed_out" ? "Time expired" : "Submitted"}</div>
            <h2 className="section-title">Results for {exam.title}</h2>
            <p className="lede">
              Your paper is finished. Review the score, the section breakdown, and every question below.
            </p>
            <div className="summary-grid" style={{ marginTop: 22 }}>
              <div className="summary-item">
                <strong>{result?.totalScore ?? 0}</strong>
                <span>final score</span>
              </div>
              <div className="summary-item">
                <strong>{result?.correctCount ?? 0}</strong>
                <span>correct</span>
              </div>
              <div className="summary-item">
                <strong>{result?.incorrectCount ?? 0}</strong>
                <span>incorrect</span>
              </div>
              <div className="summary-item">
                <strong>{result?.unansweredCount ?? 0}</strong>
                <span>blank</span>
              </div>
            </div>
            <div className="summary-grid" style={{ marginTop: 16 }}>
              {partBreakdown.map((part) => (
                <div className="summary-item" key={part.part}>
                  <strong>{part.subtotal}</strong>
                  <span>
                    {part.part.replace("_", " ").toUpperCase()} · {part.correctCount} correct · max {part.maxPoints}
                  </span>
                </div>
              ))}
            </div>
            <div className="action-row" style={{ marginTop: 24 }}>
              <button className="primary-button" type="button" onClick={restartExam}>
                Start again
              </button>
            </div>
          </div>
        </div>

        <div className="review-grid">
          {exam.questions.map((question) => {
            const questionResult = questionStatusMap.get(question.number);
            const answerSummary =
              questionResult?.status === "unanswered"
                ? "No answer submitted"
                : `Your answer: ${questionResult?.selectedLabel} · Correct: ${questionResult?.correctLabel}`;

            return (
              <article className="review-card animate-rise" key={question.id}>
                <div className="eyebrow">
                  Question {question.number} · {question.points} pts
                </div>
                <h3>{questionResult?.status === "correct" ? "Correct" : questionResult?.status === "incorrect" ? "Incorrect" : "Blank"}</h3>
                <p>{question.stemText}</p>
                <div className="status-banner" data-tone={questionResult?.status === "correct" ? "success" : "danger"}>
                  <p>{answerSummary}</p>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    );
  }

  const currentSession = activeSession as ExamSession;

  return (
    <div className="split-layout">
      <section className="hero-grid">
        <div className="panel">
          <div className="panel-inner">
            <div className="pill-row">
              <span className="stat-pill">Timer: {formatCountdown(remainingSeconds)}</span>
              <span className="stat-pill">
                {answeredNumbers.length}/{exam.questionCount} answered
              </span>
              <span className="stat-pill">{exam.rulesSummary}</span>
            </div>
            <div className="action-row" style={{ marginTop: 18 }}>
              <button className="secondary-button" type="button" onClick={() => moveQuestion(-1)}>
                Previous
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setSession(toggleMarkedQuestion(currentSession, activeQuestion.number))}
              >
                {currentSession.marked.includes(activeQuestion.number) ? "Unmark question" : "Mark for review"}
              </button>
              <button className="secondary-button" type="button" onClick={() => moveQuestion(1)}>
                Next
              </button>
              <button className="primary-button" type="button" onClick={submitCurrentExam}>
                Submit paper
              </button>
            </div>
          </div>
        </div>

        <QuestionStage
          question={activeQuestion}
          selectedLabel={currentSession.answers[activeQuestion.number] ?? null}
          onSelect={(label) => setSession(answerExamQuestion(currentSession, activeQuestion.number, label))}
          badgeText={`Mock exam · ${activeQuestion.part.replace("_", " ").toUpperCase()}`}
        />

        <div className="status-banner">
          <p>
            Answers save locally while you work. This paper uses {exam.penaltySummary.toLowerCase()}
            {!exam.officialDuration ? " The timer is inferred from this exam family." : ""}
          </p>
        </div>
      </section>

      <QuestionPalette
        numbers={exam.availableQuestionNumbers}
        currentQuestion={activeQuestion.number}
        answered={answeredNumbers}
        marked={currentSession.marked}
        onJump={(questionNumber) => setSession(jumpExamQuestion(currentSession, questionNumber))}
      />
    </div>
  );
}

function formatCountdown(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
