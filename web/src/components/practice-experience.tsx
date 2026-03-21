"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { QuestionStage } from "@/components/question-stage";
import { buildQuestionKey } from "@/lib/formatting";
import {
  buildFallbackPracticeFilters,
  ensurePracticeSession,
  getQuestionEntry,
  recordPracticeAttempt,
  resetPracticeQuestion,
  selectPracticeChoice,
  submitPracticeChoice,
} from "@/lib/session-models";
import {
  loadPracticeSession,
  loadPracticeStats,
  savePracticeSession,
  savePracticeStats,
} from "@/lib/session-storage";
import type { HydratedExam, PracticeSession, PracticeStats, QuestionIndexEntry } from "@/lib/types";

interface PracticeExperienceProps {
  exam: HydratedExam;
  questionNumber: number;
  allQuestions: QuestionIndexEntry[];
}

export function PracticeExperience({ exam, questionNumber, allQuestions }: PracticeExperienceProps) {
  const router = useRouter();
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [stats, setStats] = useState<PracticeStats>({ byQuestionKey: {} });
  const [isHydrated, setIsHydrated] = useState(false);

  const currentEntry = useMemo(() => {
    return getQuestionEntry(allQuestions, exam.examId, questionNumber);
  }, [allQuestions, exam.examId, questionNumber]);

  useEffect(() => {
    if (!currentEntry) {
      return;
    }

    const storedSession = loadPracticeSession();
    const storedStats = loadPracticeStats();
    const fallbackPool = allQuestions.filter((entry) => entry.examId === exam.examId);
    const fallbackFilters = buildFallbackPracticeFilters(currentEntry);
    const nextSession = ensurePracticeSession(storedSession, fallbackPool, fallbackFilters, currentEntry);

    setSession(nextSession);
    setStats(storedStats);
    setIsHydrated(true);
  }, [allQuestions, currentEntry, exam.examId]);

  useEffect(() => {
    if (!session) {
      return;
    }

    savePracticeSession(session);
  }, [session]);

  useEffect(() => {
    savePracticeStats(stats);
  }, [stats]);

  const currentQuestion = exam.questionLookup[questionNumber];
  const questionKey = buildQuestionKey(exam.examId, questionNumber);
  const response = session?.responses[questionKey] ?? {
    selectedLabel: null,
    submittedLabel: null,
    result: null,
    submittedAt: null,
  };
  const pool = session?.pool ?? [];
  const currentPoolIndex = pool.findIndex((entry) => entry.key === questionKey);
  const nextEntry = currentPoolIndex >= 0 ? pool[currentPoolIndex + 1] ?? null : null;
  const previousEntry = currentPoolIndex > 0 ? pool[currentPoolIndex - 1] ?? null : null;
  const questionStat = stats.byQuestionKey[questionKey];

  function navigateTo(entry: QuestionIndexEntry | null) {
    if (!entry || !session) {
      return;
    }

    setSession({
      ...session,
      currentExamId: entry.examId,
      currentQuestionNumber: entry.questionNumber,
    });
    router.push(`/practice/${entry.examId}/${entry.questionNumber}`);
  }

  function openRandomNext() {
    if (!session || pool.length <= 1) {
      return;
    }

    const alternatives = pool.filter((entry) => entry.key !== questionKey);
    const entry = alternatives[Math.floor(Math.random() * alternatives.length)];
    navigateTo(entry);
  }

  function submitAnswer() {
    if (!session || !response.selectedLabel) {
      return;
    }

    const submittedAt = new Date().toISOString();
    const nextSession = submitPracticeChoice(session, questionKey, currentQuestion.correctLabel, submittedAt);
    const correct = response.selectedLabel === currentQuestion.correctLabel;

    setSession(nextSession);
    setStats(recordPracticeAttempt(stats, questionKey, response.selectedLabel, correct, submittedAt));
  }

  if (!isHydrated || !currentEntry) {
    return (
      <section className="panel">
        <div className="panel-inner">
          <p className="lede">Loading the practice workspace...</p>
        </div>
      </section>
    );
  }

  const correctEntries = Object.entries(session?.responses ?? {})
    .filter(([, value]) => value.result === "correct")
    .map(([key]) => Number(key.split(":")[1]));
  const incorrectEntries = Object.entries(session?.responses ?? {})
    .filter(([, value]) => value.result === "incorrect")
    .map(([key]) => Number(key.split(":")[1]));

  return (
    <div className="split-layout">
      <section className="hero-grid">
        <div className="panel">
          <div className="panel-inner">
            <div className="pill-row">
              <span className="stat-pill">{session?.pool.length ?? 0} questions in this practice pool</span>
              <span className="stat-pill">{session?.filters.family === "all" ? "Mixed families" : session?.filters.family}</span>
              <span className="stat-pill">
                {Object.keys(stats.byQuestionKey).length} questions attempted locally
              </span>
            </div>
            <div className="action-row" style={{ marginTop: 18 }}>
              <button className="secondary-button" type="button" onClick={() => navigateTo(previousEntry)} disabled={!previousEntry}>
                Previous
              </button>
              <button className="secondary-button" type="button" onClick={openRandomNext} disabled={pool.length <= 1}>
                Random next
              </button>
              <button className="secondary-button" type="button" onClick={() => navigateTo(nextEntry)} disabled={!nextEntry}>
                Next
              </button>
              <button className="primary-button" type="button" onClick={submitAnswer} disabled={!response.selectedLabel || Boolean(response.result)}>
                Check answer
              </button>
            </div>
          </div>
        </div>

        <QuestionStage
          question={currentQuestion}
          selectedLabel={response.selectedLabel}
          onSelect={(label) => setSession((current) => (current ? selectPracticeChoice(current, questionKey, label) : current))}
          locked={Boolean(response.result)}
          correctLabel={response.result ? currentQuestion.correctLabel : null}
          submittedLabel={response.submittedLabel}
          badgeText={`Practice · ${currentQuestion.part.replace("_", " ").toUpperCase()}`}
        />

        {response.result ? (
          <div className="status-banner" data-tone={response.result === "correct" ? "success" : "danger"}>
            <p>
              {response.result === "correct"
                ? `Correct. ${currentQuestion.correctLabel} was the right choice, worth ${currentQuestion.points} points.`
                : `Not quite. The correct answer is ${currentQuestion.correctLabel}. This question is worth ${currentQuestion.points} points.`}
            </p>
          </div>
        ) : (
          <div className="status-banner">
            <p>Submit when you are ready to reveal the correct answer immediately.</p>
          </div>
        )}

        <div className="panel">
          <div className="panel-inner">
            <div className="eyebrow">Local stats</div>
            <div className="summary-grid" style={{ marginTop: 16 }}>
              <div className="summary-item">
                <strong>{questionStat?.attempts ?? 0}</strong>
                <span>attempts on this question</span>
              </div>
              <div className="summary-item">
                <strong>{questionStat?.correctAttempts ?? 0}</strong>
                <span>correct attempts</span>
              </div>
              <div className="summary-item">
                <strong>{questionStat?.incorrectAttempts ?? 0}</strong>
                <span>incorrect attempts</span>
              </div>
            </div>
            <div className="action-row" style={{ marginTop: 18 }}>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setSession((current) => (current ? resetPracticeQuestion(current, questionKey) : current))}
              >
                Reset this question
              </button>
            </div>
          </div>
        </div>
      </section>

      <aside className="sidebar-column">
        <section className="panel drawer">
          <div className="panel-inner">
            <div className="eyebrow">Navigator</div>
            <h3 className="section-title" style={{ fontSize: "1.6rem", marginBottom: 6 }}>
              Practice pool
            </h3>
            <p className="lede">Jump anywhere in the current filtered pool.</p>
            <div className="divider" />
            <div className="field-stack">
              {groupEntriesByExam(pool).map(([examTitle, entries]) => (
                <div key={examTitle}>
                  <p className="subtle" style={{ margin: "0 0 10px" }}>
                    {examTitle}
                  </p>
                  <div className="palette-grid">
                    {entries.map((entry) => {
                      const entryResponse = session?.responses[entry.key];
                      return (
                        <button
                          type="button"
                          className="palette-button"
                          key={entry.key}
                          data-current={entry.key === questionKey}
                          data-correct={entryResponse?.result === "correct"}
                          data-incorrect={entryResponse?.result === "incorrect"}
                          onClick={() => navigateTo(entry)}
                          aria-label={`Open ${entry.examTitle} question ${entry.questionNumber}`}
                        >
                          {entry.questionNumber}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </aside>
    </div>
  );
}

function groupEntriesByExam(pool: QuestionIndexEntry[]) {
  const groups = new Map<string, QuestionIndexEntry[]>();

  for (const entry of pool) {
    const current = groups.get(entry.examTitle) ?? [];
    current.push(entry);
    groups.set(entry.examTitle, current);
  }

  return Array.from(groups.entries());
}
