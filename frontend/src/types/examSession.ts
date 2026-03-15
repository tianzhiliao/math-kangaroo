export type ExamMode = 'practice' | 'real'

export type SubmitReason = 'manual' | 'timeout' | 'practice_finish'
export type QuestionKeyVersion = 1 | 2

export type QuestionStatusTone =
  | 'answered'
  | 'unanswered'
  | 'correct'
  | 'incorrect'

export interface ExamSession {
  examId: string
  mode: ExamMode
  questionKeyVersion: QuestionKeyVersion
  startedAt: number
  submittedAt: number | null
  submitReason: SubmitReason | null
  currentQuestionIndex: number
  answers: Record<number, string>
  submittedQuestionIds: number[]
}

export interface QuestionStatus {
  questionId: number
  questionIndex: number
  tone: QuestionStatusTone
  isSelected?: boolean
}

export type QuestionResultTone = 'correct' | 'incorrect' | 'unanswered'

export interface QuestionResult {
  questionId: number
  questionIndex: number
  questionNumber: number
  tone: QuestionResultTone
  userAnswer: string | null
  correctAnswer: string
  points: number
  scoreDelta: number
}

export interface ExamResult {
  mode: ExamMode
  score: number
  scoreLabel: string
  maxScore: number
  correctCount: number
  incorrectCount: number
  unansweredCount: number
  answeredCount: number
  accuracy: number
  elapsedSeconds: number
  submitReason: SubmitReason
  questionResults: QuestionResult[]
}

export interface PracticeResumeSummary {
  checkedCount: number
  answeredCount: number
  currentQuestionIndex: number
  currentQuestionNumber: number
}
