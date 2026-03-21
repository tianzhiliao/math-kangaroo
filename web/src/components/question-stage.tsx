"use client";

import type { ExamQuestion } from "@/lib/types";

type ChoiceResult = "correct" | "incorrect" | "neutral";

interface QuestionStageProps {
  question: ExamQuestion;
  selectedLabel: string | null;
  onSelect: (label: string) => void;
  locked?: boolean;
  correctLabel?: string | null;
  submittedLabel?: string | null;
  badgeText?: string;
}

export function QuestionStage({
  question,
  selectedLabel,
  onSelect,
  locked = false,
  correctLabel = null,
  submittedLabel = null,
  badgeText,
}: QuestionStageProps) {
  return (
    <section className="question-stage animate-rise">
      <div className="question-heading">
        <div>
          <div className="eyebrow">{badgeText ?? `${formatPart(question.part)} · ${question.points} pts`}</div>
          <h2 className="question-number">Question {question.number}</h2>
        </div>
        <div className="pill-row">
          <span className="mini-pill">{question.points} point{question.points === 1 ? "" : "s"}</span>
        </div>
      </div>
      {question.stemText ? <p className="question-text">{question.stemText}</p> : null}
      {question.stemAssets.length > 0 ? (
        <div className="asset-stack">
          {question.stemAssets.map((asset) => (
            <div className="asset-card" key={asset.id}>
              <img
                src={asset.url}
                alt={`Illustration for question ${question.number}`}
                width={asset.width}
                height={asset.height}
              />
            </div>
          ))}
        </div>
      ) : null}
      <div className="choice-grid">
        {question.choices.map((choice) => {
          const result = getChoiceResult(choice.label, correctLabel, submittedLabel);
          return (
            <button
              className="choice-card"
              type="button"
              key={choice.label}
              data-selected={selectedLabel === choice.label}
              data-result={result === "neutral" ? undefined : result}
              onClick={() => onSelect(choice.label)}
              disabled={locked}
            >
              <span className="choice-badge">{choice.label}</span>
              <span className="choice-content">
                {choice.text ? <span className="choice-text">{choice.text}</span> : null}
                {choice.assets.length > 0 ? (
                  <span className="asset-stack">
                    {choice.assets.map((asset) => (
                      <span className="asset-card" key={asset.id}>
                        <img
                          src={asset.url}
                          alt={`Option ${choice.label} diagram`}
                          width={asset.width}
                          height={asset.height}
                        />
                      </span>
                    ))}
                  </span>
                ) : null}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function formatPart(part: ExamQuestion["part"]) {
  if (part === "part_a") {
    return "Part A";
  }
  if (part === "part_b") {
    return "Part B";
  }
  return "Part C";
}

function getChoiceResult(
  choiceLabel: string,
  correctLabel: string | null,
  submittedLabel: string | null,
): ChoiceResult {
  if (!correctLabel) {
    return "neutral";
  }

  if (choiceLabel === correctLabel) {
    return "correct";
  }

  if (choiceLabel === submittedLabel) {
    return "incorrect";
  }

  return "neutral";
}
