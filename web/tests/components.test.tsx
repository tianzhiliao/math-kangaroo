import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { QuestionPalette } from "@/components/question-palette";
import { QuestionStage } from "@/components/question-stage";
import { PracticeLibrary } from "@/components/practice-library";
import type { ExamQuestion, ExamSummary, QuestionIndexEntry } from "@/lib/types";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
  }),
}));

describe("question UI components", () => {
  it("allows choice selection on the question stage", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const question: ExamQuestion = {
      id: "q1",
      number: 1,
      part: "part_a",
      points: 3,
      stemText: "How many kangaroos?",
      rawStemText: "How many kangaroos?",
      stemAssets: [],
      choices: [
        { label: "A", text: "3", rawText: "3", assets: [] },
        { label: "B", text: "4", rawText: "4", assets: [] },
      ],
      correctLabel: "A",
    };

    render(<QuestionStage question={question} selectedLabel={null} onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: /A/i }));

    expect(onSelect).toHaveBeenCalledWith("A");
  });

  it("fires jumps from the question palette", async () => {
    const user = userEvent.setup();
    const onJump = vi.fn();

    render(<QuestionPalette numbers={[1, 2, 3]} currentQuestion={2} answered={[1]} onJump={onJump} />);
    await user.click(screen.getByRole("button", { name: "3" }));

    expect(onJump).toHaveBeenCalledWith(3);
  });
});

describe("practice library", () => {
  it("filters the pool and saves a session before routing", async () => {
    const user = userEvent.setup();
    const exams: ExamSummary[] = [
      {
        examId: "canada-2023",
        title: "Canada Grade 1-2 2023",
        subtitle: "Canada · 2023 · 18 questions",
        family: "canada_gr0102e_18",
        familyLabel: "Canada Grade 1-2",
        originLabel: "Canada",
        year: 2023,
        level: "grade-1-2",
        language: "en",
        questionCount: 18,
        durationMinutes: 45,
        maxScore: 90,
        startingPoints: 18,
        penaltyMode: "minus_one",
        rulesSummary: "Q1-6: 3 pts · Q7-12: 4 pts · Q13-18: 5 pts",
        penaltySummary: "Incorrect answers deduct 1 point. Blanks are worth 0.",
        officialDuration: true,
        availableQuestionNumbers: [1, 2],
      },
    ];
    const questionIndex: QuestionIndexEntry[] = [
      {
        key: "canada-2023:1",
        examId: "canada-2023",
        examTitle: "Canada Grade 1-2 2023",
        family: "canada_gr0102e_18",
        familyLabel: "Canada Grade 1-2",
        year: 2023,
        questionNumber: 1,
        part: "part_a",
        points: 3,
      },
      {
        key: "canada-2023:2",
        examId: "canada-2023",
        examTitle: "Canada Grade 1-2 2023",
        family: "canada_gr0102e_18",
        familyLabel: "Canada Grade 1-2",
        year: 2023,
        questionNumber: 2,
        part: "part_a",
        points: 3,
      },
    ];

    render(<PracticeLibrary exams={exams} questionIndex={questionIndex} />);
    await user.click(screen.getByRole("button", { name: /Open question 1/i }));

    const stored = window.localStorage.getItem("kangaroo.practice.session");

    expect(stored).toContain("canada-2023");
    expect(push).toHaveBeenCalledWith("/practice/canada-2023/1");
  });
});
