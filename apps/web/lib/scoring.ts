import type { Exam, ScoringRule } from "./types";

export function pointsForQuestionNumber(
  questionNumber: number,
  rules: ScoringRule[],
): number {
  for (const r of rules) {
    if (questionNumber >= r.from && questionNumber <= r.to) {
      return r.points;
    }
  }
  return 0;
}

export type TierBreakdown = {
  from: number;
  to: number;
  points: number;
  /** Points earned from correct answers in this tier (wrong-answer penalties excluded). */
  earned: number;
  max: number;
};

/**
 * Per-tier points from correct answers, for the result score card.
 * question_count + Σ earned − wrong count = the untruncated computeExamScore total.
 */
export function computeTierBreakdown(
  exam: Exam,
  answers: Record<number, string | null | undefined>,
): TierBreakdown[] {
  return exam.scoring_rules.map((rule) => {
    let earned = 0;
    let max = 0;
    for (let q = rule.from; q <= Math.min(rule.to, exam.question_count); q++) {
      max += rule.points;
      const selected = answers[q];
      if (selected && selected === exam.answer_key[String(q)]) {
        earned += rule.points;
      }
    }
    return { from: rule.from, to: rule.to, points: rule.points, earned, max };
  });
}

/**
 * Kangaroo-style scoring: start from N points (N = question count),
 * add tier points for each correct, subtract 1 for each wrong, unanswered neutral.
 */
export function computeExamScore(
  exam: Exam,
  answers: Record<number, string | null | undefined>,
): {
  score: number;
  maxScore: number;
  perQuestion: Record<
    number,
    { correct: boolean | null; selected: string | null; expected: string }
  >;
} {
  const n = exam.question_count;
  let score = n;
  const perQuestion: Record<
    number,
    { correct: boolean | null; selected: string | null; expected: string }
  > = {};

  let maxScore = n;
  for (let q = 1; q <= n; q++) {
    maxScore += pointsForQuestionNumber(q, exam.scoring_rules);
  }

  for (let q = 1; q <= n; q++) {
    const expected = exam.answer_key[String(q)] ?? "";
    const selected = answers[q] ?? null;
    if (!selected) {
      perQuestion[q] = { correct: null, selected, expected };
      continue;
    }
    if (selected === expected) {
      score += pointsForQuestionNumber(q, exam.scoring_rules);
      perQuestion[q] = { correct: true, selected, expected };
    } else {
      score -= 1;
      perQuestion[q] = { correct: false, selected, expected };
    }
  }

  return { score: Math.max(0, score), maxScore, perQuestion };
}
