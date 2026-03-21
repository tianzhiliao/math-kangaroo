import type {
  ExamQuestion,
  ExamResult,
  ExamResultQuestion,
  ExamSummary,
  HydratedExam,
  PenaltyMode,
  ScoringProfile,
  ScoringRule,
} from "@/lib/types";

const FAMILY_BASELINE: Record<
  ExamSummary["family"],
  {
    startingPoints: number;
    durationMinutes: number;
    penaltyMode: PenaltyMode;
    familyLabel: string;
    originLabel: string;
  }
> = {
  canada_gr0102e_18: {
    startingPoints: 18,
    durationMinutes: 45,
    penaltyMode: "minus_one",
    familyLabel: "Canada Grade 1-2",
    originLabel: "Canada",
  },
  felix_austria_15: {
    startingPoints: 15,
    durationMinutes: 60,
    penaltyMode: "minus_quarter",
    familyLabel: "Felix Austria",
    originLabel: "Austria",
  },
  felix_brazil_24: {
    startingPoints: 24,
    durationMinutes: 100,
    penaltyMode: "minus_quarter",
    familyLabel: "Felix Brazil",
    originLabel: "Brazil",
  },
};

export function getFamilyMeta(family: ExamSummary["family"]) {
  return FAMILY_BASELINE[family];
}

export function resolveScoringProfile(input: {
  family: ExamSummary["family"];
  durationMinutes: number | null;
  scoringRules: ScoringRule[];
}): ScoringProfile {
  const familyMeta = getFamilyMeta(input.family);
  const durationMinutes = input.durationMinutes ?? familyMeta.durationMinutes;
  const officialDuration = input.durationMinutes !== null;
  const maxQuestionPoints = input.scoringRules.reduce(
    (total, rule) => total + (rule.to - rule.from + 1) * rule.points,
    0,
  );

  return {
    family: input.family,
    startingPoints: familyMeta.startingPoints,
    penaltyMode: familyMeta.penaltyMode,
    durationMinutes,
    maxScore: familyMeta.startingPoints + maxQuestionPoints,
    officialDuration,
    rulesSummary: input.scoringRules
      .map((rule) => `Q${rule.from}-${rule.to}: ${rule.points} pts`)
      .join(" · "),
    penaltySummary:
      familyMeta.penaltyMode === "minus_one"
        ? "Incorrect answers deduct 1 point. Blanks are worth 0."
        : "Incorrect answers deduct 25% of that question's value. Blanks are worth 0.",
  };
}

export function getPenalty(points: number, penaltyMode: PenaltyMode) {
  if (penaltyMode === "minus_one") {
    return 1;
  }

  return points * 0.25;
}

export function scoreExamAttempt(
  exam: Pick<HydratedExam, "questions" | "maxScore" | "startingPoints" | "penaltyMode">,
  answers: Record<number, string>,
  elapsedSeconds: number,
  submittedAt: string,
): ExamResult {
  const questionResults: ExamResultQuestion[] = exam.questions.map((question) =>
    scoreQuestion(question, answers[question.number], exam.penaltyMode),
  );
  const earnedPoints = questionResults
    .filter((result) => result.status === "correct")
    .reduce((total, result) => total + result.pointsDelta, 0);
  const penaltyPoints = questionResults
    .filter((result) => result.status === "incorrect")
    .reduce((total, result) => total + Math.abs(result.pointsDelta), 0);
  const totalScore = clampScore(exam.startingPoints + earnedPoints - penaltyPoints);

  return {
    totalScore,
    correctCount: questionResults.filter((result) => result.status === "correct").length,
    incorrectCount: questionResults.filter((result) => result.status === "incorrect").length,
    unansweredCount: questionResults.filter((result) => result.status === "unanswered").length,
    maxScore: exam.maxScore,
    startingPoints: exam.startingPoints,
    earnedPoints,
    penaltyPoints,
    submittedAt,
    elapsedSeconds,
    questionResults,
  };
}

function scoreQuestion(
  question: Pick<ExamQuestion, "number" | "points" | "correctLabel">,
  selectedLabel: string | undefined,
  penaltyMode: PenaltyMode,
): ExamResultQuestion {
  if (!selectedLabel) {
    return {
      questionNumber: question.number,
      correctLabel: question.correctLabel,
      selectedLabel: null,
      status: "unanswered",
      pointsDelta: 0,
    };
  }

  if (selectedLabel === question.correctLabel) {
    return {
      questionNumber: question.number,
      correctLabel: question.correctLabel,
      selectedLabel,
      status: "correct",
      pointsDelta: question.points,
    };
  }

  return {
    questionNumber: question.number,
    correctLabel: question.correctLabel,
    selectedLabel,
    status: "incorrect",
    pointsDelta: -getPenalty(question.points, penaltyMode),
  };
}

function clampScore(score: number) {
  return Number(score.toFixed(2));
}
