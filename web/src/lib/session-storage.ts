import type {
  ExamSession,
  PracticeSession,
  PracticeStats,
  QuestionIndexEntry,
} from "@/lib/types";

const examPrefix = "kangaroo.exam.";
const practiceSessionKey = "kangaroo.practice.session";
const practiceStatsKey = "kangaroo.practice.stats";

function isBrowser() {
  return typeof window !== "undefined";
}

export function loadExamSession(examId: string): ExamSession | null {
  if (!isBrowser()) {
    return null;
  }

  const raw = window.localStorage.getItem(`${examPrefix}${examId}`);
  return raw ? (JSON.parse(raw) as ExamSession) : null;
}

export function saveExamSession(session: ExamSession) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(`${examPrefix}${session.examId}`, JSON.stringify(session));
}

export function clearExamSession(examId: string) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(`${examPrefix}${examId}`);
}

export function loadPracticeSession(): PracticeSession | null {
  if (!isBrowser()) {
    return null;
  }

  const raw = window.localStorage.getItem(practiceSessionKey);
  return raw ? (JSON.parse(raw) as PracticeSession) : null;
}

export function savePracticeSession(session: PracticeSession) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(practiceSessionKey, JSON.stringify(session));
}

export function buildPracticePoolKey(pool: QuestionIndexEntry[]) {
  return pool.map((entry) => entry.key).join("|");
}

export function loadPracticeStats(): PracticeStats {
  if (!isBrowser()) {
    return { byQuestionKey: {} };
  }

  const raw = window.localStorage.getItem(practiceStatsKey);
  return raw ? (JSON.parse(raw) as PracticeStats) : { byQuestionKey: {} };
}

export function savePracticeStats(stats: PracticeStats) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(practiceStatsKey, JSON.stringify(stats));
}
