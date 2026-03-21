"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { formatDuration } from "@/lib/formatting";
import type { ExamSummary } from "@/lib/types";

interface ExamLibraryProps {
  exams: ExamSummary[];
}

export function ExamLibrary({ exams }: ExamLibraryProps) {
  const [family, setFamily] = useState("all");
  const [year, setYear] = useState("all");

  const familyOptions = Array.from(new Set(exams.map((exam) => exam.familyLabel)));
  const yearOptions = Array.from(new Set(exams.map((exam) => String(exam.year)))).sort((left, right) =>
    Number(right) - Number(left),
  );

  const filteredExams = useMemo(() => {
    return exams.filter((exam) => {
      if (family !== "all" && exam.familyLabel !== family) {
        return false;
      }

      if (year !== "all" && String(exam.year) !== year) {
        return false;
      }

      return true;
    });
  }, [exams, family, year]);

  return (
    <section className="hero-grid">
      <div className="panel">
        <div className="panel-inner">
          <div className="eyebrow">Selection</div>
          <h2 className="section-title">Choose a paper</h2>
          <p className="lede">
            Start from question one or jump directly into a later problem. The timer only begins after you press
            start inside the paper.
          </p>
          <div className="filter-grid">
            <div className="field-stack" style={{ minWidth: 220 }}>
              <label htmlFor="family-filter">Exam family</label>
              <select id="family-filter" value={family} onChange={(event) => setFamily(event.target.value)}>
                <option value="all">All families</option>
                {familyOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
            <div className="field-stack" style={{ minWidth: 180 }}>
              <label htmlFor="year-filter">Year</label>
              <select id="year-filter" value={year} onChange={(event) => setYear(event.target.value)}>
                <option value="all">All years</option>
                {yearOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="pill-row" style={{ marginTop: 16 }}>
            <span className="stat-pill">{filteredExams.length} papers ready</span>
            <span className="stat-pill">
              {filteredExams.reduce((total, exam) => total + exam.questionCount, 0)} questions in this view
            </span>
          </div>
        </div>
      </div>

      <div className="card-grid">
        {filteredExams.map((exam) => (
          <article className="catalog-card animate-rise" key={exam.examId}>
            <div className="field-stack">
              <div className="eyebrow">{exam.familyLabel}</div>
              <h3>{exam.title}</h3>
              <p>{exam.subtitle}</p>
            </div>
            <div className="pill-row">
              <span className="mini-pill">{exam.questionCount} questions</span>
              <span className="mini-pill">{formatDuration(exam.durationMinutes)}</span>
              <span className="mini-pill">Max {exam.maxScore}</span>
              {!exam.officialDuration ? <span className="mini-pill">Family default timing</span> : null}
            </div>
            <p>{exam.rulesSummary}</p>
            <p>{exam.penaltySummary}</p>
            <Link className="primary-button" href={`/exam/${exam.examId}`}>
              Open paper
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
