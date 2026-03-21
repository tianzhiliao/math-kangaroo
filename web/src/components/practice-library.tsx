"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { buildPracticePoolKey, savePracticeSession } from "@/lib/session-storage";
import type { ExamSummary, PracticeFilters, PracticeSession, QuestionIndexEntry } from "@/lib/types";

interface PracticeLibraryProps {
  exams: ExamSummary[];
  questionIndex: QuestionIndexEntry[];
}

export function PracticeLibrary({ exams, questionIndex }: PracticeLibraryProps) {
  const router = useRouter();
  const [filters, setFilters] = useState<PracticeFilters>({
    family: "all",
    year: "all",
    examId: "all",
  });

  const familyOptions = Array.from(new Set(exams.map((exam) => exam.familyLabel)));
  const yearOptions = Array.from(new Set(exams.map((exam) => String(exam.year)))).sort((left, right) =>
    Number(right) - Number(left),
  );

  const examOptions = useMemo(() => {
    return exams.filter((exam) => {
      if (filters.family !== "all" && exam.familyLabel !== filters.family) {
        return false;
      }
      if (filters.year !== "all" && String(exam.year) !== filters.year) {
        return false;
      }
      return true;
    });
  }, [exams, filters.family, filters.year]);

  const filteredPool = useMemo(() => {
    return questionIndex.filter((entry) => {
      if (filters.family !== "all" && entry.familyLabel !== filters.family) {
        return false;
      }
      if (filters.year !== "all" && String(entry.year) !== filters.year) {
        return false;
      }
      if (filters.examId !== "all" && entry.examId !== filters.examId) {
        return false;
      }
      return true;
    });
  }, [filters, questionIndex]);

  function updateFilter<K extends keyof PracticeFilters>(key: K, value: PracticeFilters[K]) {
    setFilters((current) => {
      const next = { ...current, [key]: value };
      if (key === "family" || key === "year") {
        const examStillVisible =
          next.examId === "all" ||
          exams.some(
            (exam) =>
              exam.examId === next.examId &&
              (next.family === "all" || exam.familyLabel === next.family) &&
              (next.year === "all" || String(exam.year) === next.year),
          );

        if (!examStillVisible) {
          next.examId = "all";
        }
      }
      return next;
    });
  }

  function openQuestion(entry: QuestionIndexEntry) {
    const session: PracticeSession = {
      poolKey: buildPracticePoolKey(filteredPool),
      filters,
      currentExamId: entry.examId,
      currentQuestionNumber: entry.questionNumber,
      pool: filteredPool,
      responses: {},
    };

    savePracticeSession(session);
    router.push(`/practice/${entry.examId}/${entry.questionNumber}`);
  }

  function openRandomQuestion() {
    if (filteredPool.length === 0) {
      return;
    }

    const entry = filteredPool[Math.floor(Math.random() * filteredPool.length)];
    openQuestion(entry);
  }

  return (
    <section className="hero-grid">
      <div className="panel">
        <div className="panel-inner">
          <div className="eyebrow">Question bank</div>
          <h2 className="section-title">Build your practice set</h2>
          <p className="lede">
            Narrow the full archive by family, year, or exact paper. You can start from a specific question or let the
            app drop you into a random one.
          </p>
          <div className="filter-grid">
            <div className="field-stack" style={{ minWidth: 220 }}>
              <label htmlFor="practice-family-filter">Exam family</label>
              <select
                id="practice-family-filter"
                value={filters.family}
                onChange={(event) => updateFilter("family", event.target.value)}
              >
                <option value="all">All families</option>
                {familyOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
            <div className="field-stack" style={{ minWidth: 180 }}>
              <label htmlFor="practice-year-filter">Year</label>
              <select
                id="practice-year-filter"
                value={filters.year}
                onChange={(event) => updateFilter("year", event.target.value)}
              >
                <option value="all">All years</option>
                {yearOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
            <div className="field-stack" style={{ minWidth: 260 }}>
              <label htmlFor="practice-exam-filter">Paper</label>
              <select
                id="practice-exam-filter"
                value={filters.examId}
                onChange={(event) => updateFilter("examId", event.target.value)}
              >
                <option value="all">All visible papers</option>
                {examOptions.map((exam) => (
                  <option key={exam.examId} value={exam.examId}>
                    {exam.title}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="pill-row" style={{ marginTop: 16 }}>
            <span className="stat-pill">{filteredPool.length} questions in pool</span>
            <button className="primary-button" type="button" onClick={openRandomQuestion} disabled={filteredPool.length === 0}>
              Start a random question
            </button>
          </div>
        </div>
      </div>

      <div className="card-grid">
        {examOptions.map((exam) => {
          const examQuestions = filteredPool.filter((entry) => entry.examId === exam.examId);

          if (examQuestions.length === 0) {
            return null;
          }

          return (
            <article className="catalog-card animate-rise" key={exam.examId}>
              <div className="field-stack">
                <div className="eyebrow">{exam.familyLabel}</div>
                <h3>{exam.title}</h3>
                <p>{examQuestions.length} visible questions in the current practice view.</p>
              </div>
              <div className="palette-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(44px, 1fr))" }}>
                {examQuestions.map((entry) => (
                  <button
                    type="button"
                    className="palette-button"
                    key={entry.key}
                    onClick={() => openQuestion(entry)}
                    aria-label={`Open question ${entry.questionNumber} from ${exam.title}`}
                  >
                    {entry.questionNumber}
                  </button>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
