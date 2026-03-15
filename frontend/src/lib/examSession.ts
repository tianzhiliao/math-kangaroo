import type { Exam } from '../types/exam'
import type {
  ExamMode,
  ExamResult,
  ExamSession,
  PracticeResumeSummary,
  QuestionResult,
  QuestionStatus,
  SubmitReason,
} from '../types/examSession'
import { getLegacyPracticeQuestionIdMap, getQuestionSessionId } from './questionIdentity'

export const REAL_EXAM_DURATION_SECONDS = 45 * 60
export const REAL_EXAM_BASE_SCORE = 18
export const REAL_EXAM_MAX_SCORE = 90
export const CURRENT_QUESTION_KEY_VERSION = 2 as const

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isExamMode(value: unknown): value is ExamMode {
  return value === 'practice' || value === 'real'
}

export function isExamModeValue(value: unknown): value is ExamMode {
  return isExamMode(value)
}

function isSubmitReason(value: unknown): value is SubmitReason {
  return value === 'manual' || value === 'timeout' || value === 'practice_finish'
}

function normalizeQuestionKeyVersion(value: unknown) {
  return value === CURRENT_QUESTION_KEY_VERSION ? CURRENT_QUESTION_KEY_VERSION : 1
}

function normalizeAnswers(value: unknown): Record<number, string> {
  if (!isObject(value)) {
    return {}
  }

  const answers: Record<number, string> = {}

  Object.entries(value).forEach(([questionId, answer]) => {
    if (typeof answer === 'string' && answer.trim().length > 0) {
      answers[Number(questionId)] = answer
    }
  })

  return answers
}

function normalizeSubmittedQuestionIds(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value.filter((item): item is number => typeof item === 'number' && Number.isFinite(item))
}

export function getExamSessionStorageKey(examId: string, mode: ExamMode) {
  return `exam_session_${examId}_${mode}`
}

export function createExamSession(
  examId: string,
  mode: ExamMode,
  startedAt = Date.now(),
): ExamSession {
  return {
    examId,
    mode,
    questionKeyVersion: CURRENT_QUESTION_KEY_VERSION,
    startedAt,
    submittedAt: null,
    submitReason: null,
    currentQuestionIndex: 0,
    answers: {},
    submittedQuestionIds: [],
  }
}

export function coerceExamSession(
  value: unknown,
  examId: string,
  mode: ExamMode,
): ExamSession | null {
  if (!isObject(value)) {
    return null
  }

  const startedAt = typeof value.startedAt === 'number' ? value.startedAt : Date.now()
  const submittedAt =
    value.submittedAt === null || typeof value.submittedAt === 'number'
      ? value.submittedAt
      : null
  const submitReason =
    value.submitReason === null || isSubmitReason(value.submitReason)
      ? value.submitReason
      : null
  const currentQuestionIndex =
    typeof value.currentQuestionIndex === 'number' && value.currentQuestionIndex >= 0
      ? Math.floor(value.currentQuestionIndex)
      : 0
  const storedMode = isExamMode(value.mode) ? value.mode : mode
  const storedExamId = typeof value.examId === 'string' ? value.examId : examId

  return {
    examId: storedExamId,
    mode: storedMode,
    questionKeyVersion: normalizeQuestionKeyVersion(value.questionKeyVersion),
    startedAt,
    submittedAt,
    submitReason,
    currentQuestionIndex,
    answers: normalizeAnswers(value.answers),
    submittedQuestionIds: normalizeSubmittedQuestionIds(value.submittedQuestionIds),
  }
}

function remapAnswers(
  answers: Record<number, string>,
  legacyQuestionIdMap: Map<number, number>,
) {
  const remappedAnswers: Record<number, string> = {}

  Object.entries(answers).forEach(([questionId, answer]) => {
    const nextQuestionId = legacyQuestionIdMap.get(Number(questionId))
    if (nextQuestionId !== undefined) {
      remappedAnswers[nextQuestionId] = answer
    }
  })

  return remappedAnswers
}

function remapSubmittedQuestionIds(
  submittedQuestionIds: number[],
  legacyQuestionIdMap: Map<number, number>,
) {
  return [...new Set(
    submittedQuestionIds.flatMap((questionId) => {
      const nextQuestionId = legacyQuestionIdMap.get(questionId)
      return nextQuestionId === undefined ? [] : [nextQuestionId]
    }),
  )]
}

export function migrateExamSessionQuestionKeys(exam: Exam, session: ExamSession): ExamSession {
  if (session.questionKeyVersion === CURRENT_QUESTION_KEY_VERSION) {
    return session
  }

  if (session.mode !== 'practice') {
    return {
      ...session,
      questionKeyVersion: CURRENT_QUESTION_KEY_VERSION,
    }
  }

  const legacyQuestionIdMap = getLegacyPracticeQuestionIdMap(exam)

  return {
    ...session,
    questionKeyVersion: CURRENT_QUESTION_KEY_VERSION,
    answers: remapAnswers(session.answers, legacyQuestionIdMap),
    submittedQuestionIds: remapSubmittedQuestionIds(
      session.submittedQuestionIds,
      legacyQuestionIdMap,
    ),
  }
}

export function getAnsweredCount(session: ExamSession) {
  return Object.keys(session.answers).length
}

export function getSubmittedCount(session: ExamSession) {
  return session.submittedQuestionIds.length
}

export function hasMeaningfulPracticeProgress(session: ExamSession | null | undefined) {
  if (
    !session ||
    session.mode !== 'practice' ||
    session.submittedAt !== null ||
    session.submitReason !== null
  ) {
    return false
  }

  return (
    session.currentQuestionIndex > 0 ||
    getAnsweredCount(session) > 0 ||
    getSubmittedCount(session) > 0
  )
}

export function getPracticeResumeSummary(
  session: ExamSession | null | undefined,
): PracticeResumeSummary | null {
  if (!hasMeaningfulPracticeProgress(session) || !session) {
    return null
  }

  return {
    checkedCount: getSubmittedCount(session),
    answeredCount: getAnsweredCount(session),
    currentQuestionIndex: session.currentQuestionIndex,
    currentQuestionNumber: session.currentQuestionIndex + 1,
  }
}

export function getSessionElapsedSeconds(session: ExamSession, now = Date.now()) {
  const endTime = session.submittedAt ?? now
  return Math.max(0, Math.floor((endTime - session.startedAt) / 1000))
}

export function getSessionRemainingSeconds(session: ExamSession, now = Date.now()) {
  if (session.mode !== 'real') {
    return null
  }

  return Math.max(0, REAL_EXAM_DURATION_SECONDS - getSessionElapsedSeconds(session, now))
}

export function getCanSubmit(exam: Exam, session: ExamSession) {
  return (
    session.mode === 'real' &&
    session.submittedAt === null &&
    getAnsweredCount(session) === exam.questions.length
  )
}

export function getLiveQuestionStatuses(exam: Exam, session: ExamSession): QuestionStatus[] {
  return exam.questions.map((question, questionIndex) => {
    const sessionQuestionId = getQuestionSessionId(question)
    const isAnswered = session.answers[sessionQuestionId] !== undefined
    const isSubmitted = session.submittedQuestionIds.includes(sessionQuestionId)

    let tone: QuestionStatus['tone'] = 'unanswered'

    if (session.mode === 'practice') {
      if (isSubmitted) {
        if (!isAnswered) {
          tone = 'unanswered'
        } else {
          tone = session.answers[sessionQuestionId] === question.answer ? 'correct' : 'incorrect'
        }
      }
    } else if (isAnswered) {
      tone = 'answered'
    }

    return {
      questionId: sessionQuestionId,
      questionIndex,
      tone,
      isSelected: questionIndex === session.currentQuestionIndex,
    }
  })
}

export function getResultQuestionStatuses(result: ExamResult): QuestionStatus[] {
  return result.questionResults.map((questionResult) => ({
    questionId: questionResult.questionId,
    questionIndex: questionResult.questionIndex,
    tone: questionResult.tone,
    isSelected: false,
  }))
}

export function calculateExamResult(
  exam: Exam,
  session: ExamSession,
  now = Date.now(),
): ExamResult | null {
  if (session.submitReason === null) {
    return null
  }

  let correctCount = 0
  let incorrectCount = 0
  let unansweredCount = 0
  let practiceScore = 0
  let realExamCorrectPoints = 0

  const questionResults: QuestionResult[] = exam.questions.map((question, questionIndex) => {
    const sessionQuestionId = getQuestionSessionId(question)
    const userAnswer = session.answers[sessionQuestionId] ?? null

    if (userAnswer === null) {
      unansweredCount += 1
      return {
        questionId: sessionQuestionId,
        questionIndex,
        questionNumber: questionIndex + 1,
        tone: 'unanswered',
        userAnswer,
        correctAnswer: question.answer,
        points: question.points,
        scoreDelta: 0,
      }
    }

    if (userAnswer === question.answer) {
      correctCount += 1
      practiceScore += question.points
      realExamCorrectPoints += question.points
      return {
        questionId: sessionQuestionId,
        questionIndex,
        questionNumber: questionIndex + 1,
        tone: 'correct',
        userAnswer,
        correctAnswer: question.answer,
        points: question.points,
        scoreDelta: session.mode === 'real' ? question.points : question.points,
      }
    }

    incorrectCount += 1
    return {
      questionId: sessionQuestionId,
      questionIndex,
      questionNumber: questionIndex + 1,
      tone: 'incorrect',
      userAnswer,
      correctAnswer: question.answer,
      points: question.points,
      scoreDelta: session.mode === 'real' ? -1 : 0,
    }
  })

  const answeredCount = correctCount + incorrectCount
  const accuracy =
    exam.questions.length > 0 ? Math.round((correctCount / exam.questions.length) * 100) : 0

  if (session.mode === 'real') {
    const score = Math.min(
      REAL_EXAM_MAX_SCORE,
      Math.max(0, REAL_EXAM_BASE_SCORE + realExamCorrectPoints - incorrectCount),
    )

    return {
      mode: session.mode,
      score,
      scoreLabel: `${score}/${REAL_EXAM_MAX_SCORE}`,
      maxScore: REAL_EXAM_MAX_SCORE,
      correctCount,
      incorrectCount,
      unansweredCount,
      answeredCount,
      accuracy,
      elapsedSeconds: getSessionElapsedSeconds(session, now),
      submitReason: session.submitReason,
      questionResults,
    }
  }

  const maxScore = exam.questions.reduce((total, question) => total + question.points, 0)

  return {
    mode: session.mode,
    score: practiceScore,
    scoreLabel: `${practiceScore}/${maxScore}`,
    maxScore,
    correctCount,
    incorrectCount,
    unansweredCount,
    answeredCount,
    accuracy,
    elapsedSeconds: getSessionElapsedSeconds(session, now),
    submitReason: session.submitReason,
    questionResults,
  }
}

export function formatDuration(totalSeconds: number) {
  const safeSeconds = Math.max(0, totalSeconds)
  const minutes = Math.floor(safeSeconds / 60)
  const seconds = safeSeconds % 60
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}
