export type ExamFamily =
  | "canada_gr0102e_18"
  | "felix_austria_15"
  | "felix_brazil_24";

export type PenaltyMode = "minus_one" | "minus_quarter";
export type PartName = "part_a" | "part_b" | "part_c";
export type SessionStatus = "idle" | "in_progress" | "submitted" | "timed_out";

export interface ScoringRule {
  from: number;
  to: number;
  points: number;
}

export interface ScoringProfile {
  family: ExamFamily;
  startingPoints: number;
  penaltyMode: PenaltyMode;
  durationMinutes: number;
  maxScore: number;
  officialDuration: boolean;
  rulesSummary: string;
  penaltySummary: string;
}

export interface QuestionAsset {
  id: string;
  url: string;
  width: number;
  height: number;
  kind: string;
  role: string;
  mediaType: string;
}

export interface AnswerChoice {
  label: string;
  text: string;
  rawText: string;
  assets: QuestionAsset[];
}

export interface ExamQuestion {
  id: string;
  number: number;
  part: PartName;
  points: number;
  stemText: string;
  rawStemText: string;
  stemAssets: QuestionAsset[];
  choices: AnswerChoice[];
  correctLabel: string;
}

export interface ExamSummary {
  examId: string;
  title: string;
  subtitle: string;
  family: ExamFamily;
  familyLabel: string;
  originLabel: string;
  year: number;
  level: string;
  language: string;
  questionCount: number;
  durationMinutes: number;
  maxScore: number;
  startingPoints: number;
  penaltyMode: PenaltyMode;
  rulesSummary: string;
  penaltySummary: string;
  officialDuration: boolean;
  availableQuestionNumbers: number[];
}

export interface NormalizedExam extends ExamSummary {
  instructions: string[];
  rawInstructions: string[];
  questions: ExamQuestion[];
}

export interface HydratedExam extends NormalizedExam {
  questionLookup: Record<number, ExamQuestion>;
}

export interface QuestionIndexEntry {
  key: string;
  examId: string;
  examTitle: string;
  family: ExamFamily;
  familyLabel: string;
  year: number;
  questionNumber: number;
  part: PartName;
  points: number;
}

export interface CatalogData {
  generatedAt: string;
  examCount: number;
  questionCount: number;
  exams: ExamSummary[];
  questionIndex: QuestionIndexEntry[];
}

export interface ExamResultQuestion {
  questionNumber: number;
  correctLabel: string;
  selectedLabel: string | null;
  status: "correct" | "incorrect" | "unanswered";
  pointsDelta: number;
}

export interface ExamResult {
  totalScore: number;
  correctCount: number;
  incorrectCount: number;
  unansweredCount: number;
  maxScore: number;
  startingPoints: number;
  earnedPoints: number;
  penaltyPoints: number;
  submittedAt: string;
  elapsedSeconds: number;
  questionResults: ExamResultQuestion[];
}

export interface ExamSession {
  examId: string;
  status: SessionStatus;
  startQuestionNumber: number;
  currentQuestionNumber: number;
  answers: Record<number, string>;
  marked: number[];
  viewed: number[];
  startedAt: string | null;
  expiresAt: string | null;
  submittedAt: string | null;
  result: ExamResult | null;
}

export interface PracticeQuestionStat {
  attempts: number;
  correctAttempts: number;
  incorrectAttempts: number;
  lastAttemptedAt: string;
  lastSelectedLabel: string;
}

export interface PracticeStats {
  byQuestionKey: Record<string, PracticeQuestionStat>;
}

export interface PracticeSessionEntry {
  selectedLabel: string | null;
  submittedLabel: string | null;
  result: "correct" | "incorrect" | null;
  submittedAt: string | null;
}

export interface PracticeFilters {
  family: string;
  year: string;
  examId: string;
}

export interface PracticeSession {
  poolKey: string;
  filters: PracticeFilters;
  currentExamId: string;
  currentQuestionNumber: number;
  pool: QuestionIndexEntry[];
  responses: Record<string, PracticeSessionEntry>;
}
