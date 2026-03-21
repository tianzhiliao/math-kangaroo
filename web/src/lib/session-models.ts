import { scoreExamAttempt } from "@/lib/scoring";
import { buildQuestionKey } from "@/lib/formatting";
import type {
  ExamResult,
  ExamSession,
  HydratedExam,
  PracticeFilters,
  PracticeSession,
  PracticeStats,
  QuestionIndexEntry,
} from "@/lib/types";

export function createExamSession(exam: HydratedExam, startQuestionNumber: number): ExamSession {
  const startedAt = new Date().toISOString();
  const expiresAt = new Date(Date.now() + exam.durationMinutes * 60_000).toISOString();

  return {
    examId: exam.examId,
    status: "in_progress",
    startQuestionNumber,
    currentQuestionNumber: startQuestionNumber,
    answers: {},
    marked: [],
    viewed: [startQuestionNumber],
    startedAt,
    expiresAt,
    submittedAt: null,
    result: null,
  };
}

export function getRemainingSeconds(session: Pick<ExamSession, "status" | "expiresAt">, now = Date.now()) {
  if (session.status !== "in_progress" || !session.expiresAt) {
    return 0;
  }

  return Math.max(0, Math.ceil((new Date(session.expiresAt).getTime() - now) / 1000));
}

export function answerExamQuestion(session: ExamSession, questionNumber: number, label: string): ExamSession {
  return {
    ...session,
    answers: {
      ...session.answers,
      [questionNumber]: label,
    },
  };
}

export function jumpExamQuestion(session: ExamSession, questionNumber: number): ExamSession {
  return {
    ...session,
    currentQuestionNumber: questionNumber,
    viewed: Array.from(new Set([...session.viewed, questionNumber])).sort((left, right) => left - right),
  };
}

export function toggleMarkedQuestion(session: ExamSession, questionNumber: number): ExamSession {
  const marked = new Set(session.marked);

  if (marked.has(questionNumber)) {
    marked.delete(questionNumber);
  } else {
    marked.add(questionNumber);
  }

  return {
    ...session,
    marked: Array.from(marked).sort((left, right) => left - right),
  };
}

export function submitExamSession(
  session: ExamSession,
  exam: HydratedExam,
  status: "submitted" | "timed_out",
  submittedAt = new Date().toISOString(),
): ExamSession {
  const startedAtMs = session.startedAt ? new Date(session.startedAt).getTime() : Date.now();
  const elapsedSeconds = Math.max(0, Math.round((new Date(submittedAt).getTime() - startedAtMs) / 1000));
  const result = scoreExamAttempt(exam, session.answers, elapsedSeconds, submittedAt);

  return {
    ...session,
    status,
    submittedAt,
    result,
  };
}

export function createPracticeSession(
  pool: QuestionIndexEntry[],
  filters: PracticeFilters,
  current: QuestionIndexEntry,
): PracticeSession {
  return {
    poolKey: pool.map((entry) => entry.key).join("|"),
    filters,
    currentExamId: current.examId,
    currentQuestionNumber: current.questionNumber,
    pool,
    responses: {},
  };
}

export function ensurePracticeSession(
  session: PracticeSession | null,
  fallbackPool: QuestionIndexEntry[],
  filters: PracticeFilters,
  current: QuestionIndexEntry,
): PracticeSession {
  const questionExists = session?.pool.some((entry) => entry.key === current.key);

  if (!session || !questionExists) {
    return createPracticeSession(fallbackPool, filters, current);
  }

  return {
    ...session,
    currentExamId: current.examId,
    currentQuestionNumber: current.questionNumber,
  };
}

export function selectPracticeChoice(session: PracticeSession, key: string, label: string): PracticeSession {
  const previous = session.responses[key] ?? {
    selectedLabel: null,
    submittedLabel: null,
    result: null,
    submittedAt: null,
  };

  return {
    ...session,
    responses: {
      ...session.responses,
      [key]: {
        ...previous,
        selectedLabel: label,
      },
    },
  };
}

export function submitPracticeChoice(
  session: PracticeSession,
  key: string,
  correctLabel: string,
  submittedAt = new Date().toISOString(),
): PracticeSession {
  const current = session.responses[key];

  if (!current?.selectedLabel) {
    return session;
  }

  return {
    ...session,
    responses: {
      ...session.responses,
      [key]: {
        ...current,
        submittedLabel: current.selectedLabel,
        result: current.selectedLabel === correctLabel ? "correct" : "incorrect",
        submittedAt,
      },
    },
  };
}

export function resetPracticeQuestion(session: PracticeSession, key: string): PracticeSession {
  return {
    ...session,
    responses: {
      ...session.responses,
      [key]: {
        selectedLabel: null,
        submittedLabel: null,
        result: null,
        submittedAt: null,
      },
    },
  };
}

export function recordPracticeAttempt(
  stats: PracticeStats,
  key: string,
  submittedLabel: string,
  correct: boolean,
  submittedAt = new Date().toISOString(),
): PracticeStats {
  const previous = stats.byQuestionKey[key];

  return {
    byQuestionKey: {
      ...stats.byQuestionKey,
      [key]: {
        attempts: (previous?.attempts ?? 0) + 1,
        correctAttempts: (previous?.correctAttempts ?? 0) + (correct ? 1 : 0),
        incorrectAttempts: (previous?.incorrectAttempts ?? 0) + (correct ? 0 : 1),
        lastAttemptedAt: submittedAt,
        lastSelectedLabel: submittedLabel,
      },
    },
  };
}

export function getQuestionEntry(pool: QuestionIndexEntry[], examId: string, questionNumber: number) {
  const key = buildQuestionKey(examId, questionNumber);
  return pool.find((entry) => entry.key === key) ?? null;
}

export function buildFallbackPracticeFilters(entry: QuestionIndexEntry): PracticeFilters {
  return {
    family: entry.familyLabel,
    year: String(entry.year),
    examId: entry.examId,
  };
}

export function getPartBreakdown(exam: HydratedExam, result: ExamResult | null) {
  if (!result) {
    return [];
  }

  return ["part_a", "part_b", "part_c"].map((part) => {
    const partQuestions = exam.questions.filter((question) => question.part === part);
    const partNumbers = new Set(partQuestions.map((question) => question.number));
    const questionResults = result.questionResults.filter((question) => partNumbers.has(question.questionNumber));
    const subtotal = questionResults.reduce((total, question) => total + question.pointsDelta, 0);
    const maxPoints = partQuestions.reduce((total, question) => total + question.points, 0);

    return {
      part,
      subtotal,
      maxPoints,
      correctCount: questionResults.filter((question) => question.status === "correct").length,
    };
  });
}
