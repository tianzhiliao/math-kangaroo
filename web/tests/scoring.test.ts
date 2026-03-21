import { resolveScoringProfile, scoreExamAttempt } from "@/lib/scoring";
import type { HydratedExam } from "@/lib/types";

function buildExam(family: HydratedExam["family"], durationMinutes: number, points: number[]) {
  const questions = points.map((value, index) => ({
    id: `q${index + 1}`,
    number: index + 1,
    part: index < points.length / 3 ? "part_a" : index < (points.length / 3) * 2 ? "part_b" : "part_c",
    points: value,
    stemText: `Question ${index + 1}`,
    rawStemText: `Question ${index + 1}`,
    stemAssets: [],
    choices: [
      { label: "A", text: "Alpha", rawText: "Alpha", assets: [] },
      { label: "B", text: "Beta", rawText: "Beta", assets: [] },
    ],
    correctLabel: "A",
  }));

  const base = resolveScoringProfile({
    family,
    durationMinutes,
    scoringRules: [
      { from: 1, to: Math.ceil(points.length / 3), points: points[0] },
      {
        from: Math.ceil(points.length / 3) + 1,
        to: Math.ceil((points.length / 3) * 2),
        points: points[Math.ceil(points.length / 3)],
      },
      {
        from: Math.ceil((points.length / 3) * 2) + 1,
        to: points.length,
        points: points[points.length - 1],
      },
    ],
  });

  return {
    examId: `${family}-sample`,
    title: "Sample",
    subtitle: "Sample",
    level: "sample",
    language: "en",
    family,
    familyLabel: "Sample family",
    originLabel: "Sample",
    questionCount: points.length,
    availableQuestionNumbers: questions.map((question) => question.number),
    instructions: [],
    rawInstructions: [],
    questions,
    questionLookup: Object.fromEntries(questions.map((question) => [question.number, question])),
    ...base,
  } satisfies HydratedExam;
}

describe("family scoring rules", () => {
  it("scores Canada papers with -1 penalties and 18 starting points", () => {
    const exam = buildExam("canada_gr0102e_18", 45, [3, 3, 3]);
    const result = scoreExamAttempt(exam, { 1: "A", 2: "B" }, 120, "2026-03-20T12:00:00.000Z");

    expect(result.totalScore).toBe(20);
    expect(result.correctCount).toBe(1);
    expect(result.incorrectCount).toBe(1);
    expect(result.unansweredCount).toBe(1);
  });

  it("scores Felix Austria papers with quarter-point penalties and 15 starting points", () => {
    const exam = buildExam("felix_austria_15", 60, [3, 4, 5]);
    const result = scoreExamAttempt(exam, { 1: "B", 2: "A" }, 120, "2026-03-20T12:00:00.000Z");

    expect(result.totalScore).toBe(18.25);
    expect(result.penaltyPoints).toBe(0.75);
  });

  it("scores Felix Brazil papers with family default timing and a 24-point baseline", () => {
    const profile = resolveScoringProfile({
      family: "felix_brazil_24",
      durationMinutes: null,
      scoringRules: [
        { from: 1, to: 8, points: 3 },
        { from: 9, to: 16, points: 4 },
        { from: 17, to: 24, points: 5 },
      ],
    });

    expect(profile.durationMinutes).toBe(100);
    expect(profile.startingPoints).toBe(24);
    expect(profile.maxScore).toBe(120);
  });
});
