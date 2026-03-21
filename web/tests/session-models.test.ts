import {
  answerExamQuestion,
  createExamSession,
  createPracticeSession,
  getRemainingSeconds,
  recordPracticeAttempt,
  resetPracticeQuestion,
  selectPracticeChoice,
  submitExamSession,
  submitPracticeChoice,
} from "@/lib/session-models";
import type { HydratedExam, QuestionIndexEntry } from "@/lib/types";

const exam: HydratedExam = {
  examId: "sample-exam",
  title: "Sample exam",
  subtitle: "Sample",
  family: "canada_gr0102e_18",
  familyLabel: "Canada",
  originLabel: "Canada",
  year: 2023,
  level: "grade-1-2",
  language: "en",
  questionCount: 2,
  durationMinutes: 45,
  maxScore: 24,
  startingPoints: 18,
  penaltyMode: "minus_one",
  rulesSummary: "Q1-2: 3 pts",
  penaltySummary: "Incorrect answers deduct 1 point. Blanks are worth 0.",
  officialDuration: true,
  availableQuestionNumbers: [1, 2],
  instructions: [],
  rawInstructions: [],
  questions: [
    {
      id: "q1",
      number: 1,
      part: "part_a",
      points: 3,
      stemText: "Q1",
      rawStemText: "Q1",
      stemAssets: [],
      choices: [],
      correctLabel: "A",
    },
    {
      id: "q2",
      number: 2,
      part: "part_a",
      points: 3,
      stemText: "Q2",
      rawStemText: "Q2",
      stemAssets: [],
      choices: [],
      correctLabel: "B",
    },
  ],
  questionLookup: {
    1: {
      id: "q1",
      number: 1,
      part: "part_a",
      points: 3,
      stemText: "Q1",
      rawStemText: "Q1",
      stemAssets: [],
      choices: [],
      correctLabel: "A",
    },
    2: {
      id: "q2",
      number: 2,
      part: "part_a",
      points: 3,
      stemText: "Q2",
      rawStemText: "Q2",
      stemAssets: [],
      choices: [],
      correctLabel: "B",
    },
  },
};

const pool: QuestionIndexEntry[] = [
  {
    key: "sample-exam:1",
    examId: "sample-exam",
    examTitle: "Sample exam",
    family: "canada_gr0102e_18",
    familyLabel: "Canada",
    year: 2023,
    questionNumber: 1,
    part: "part_a",
    points: 3,
  },
];

describe("session models", () => {
  it("creates and submits a timed exam session", () => {
    const started = createExamSession(exam, 1);
    const answered = answerExamQuestion(started, 1, "A");
    const submitted = submitExamSession(
      answered,
      exam,
      "submitted",
      new Date(new Date(answered.startedAt ?? Date.now()).getTime() + 10_000).toISOString(),
    );

    expect(started.status).toBe("in_progress");
    expect(getRemainingSeconds(started)).toBeGreaterThan(0);
    expect(submitted.result?.totalScore).toBe(21);
    expect(submitted.status).toBe("submitted");
  });

  it("tracks practice selections, submissions, resets, and stats", () => {
    const session = createPracticeSession(
      pool,
      { family: "Canada", year: "2023", examId: "sample-exam" },
      pool[0],
    );
    const selected = selectPracticeChoice(session, "sample-exam:1", "A");
    const submitted = submitPracticeChoice(selected, "sample-exam:1", "A", "2026-03-20T12:00:00.000Z");
    const reset = resetPracticeQuestion(submitted, "sample-exam:1");
    const stats = recordPracticeAttempt(
      { byQuestionKey: {} },
      "sample-exam:1",
      "A",
      true,
      "2026-03-20T12:00:00.000Z",
    );

    expect(submitted.responses["sample-exam:1"].result).toBe("correct");
    expect(reset.responses["sample-exam:1"].result).toBeNull();
    expect(stats.byQuestionKey["sample-exam:1"].correctAttempts).toBe(1);
  });
});
