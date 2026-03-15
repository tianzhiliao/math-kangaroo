import type { ExamMode } from '../types/examSession'

export type RestoreOutcome = 'restoring' | 'loaded' | 'missing'

interface ResultPageRouteInput {
  restoreOutcome: RestoreOutcome
  hasCurrentExam: boolean
  hasSession: boolean
  sessionMode: ExamMode | null
  isSubmitted: boolean
  hasResult: boolean
}

export function getPracticeDoneRoute({
  restoreOutcome,
  hasCurrentExam,
  hasSession,
  sessionMode,
  isSubmitted,
  hasResult,
}: ResultPageRouteInput) {
  if (restoreOutcome === 'restoring') {
    return 'loading'
  }

  if (restoreOutcome === 'missing') {
    return 'toHome'
  }

  if (!hasCurrentExam || !hasSession) {
    return 'loading'
  }

  if (sessionMode !== 'practice') {
    return 'toHome'
  }

  if (!isSubmitted) {
    return 'toPractice'
  }

  if (!hasResult) {
    return 'toHome'
  }

  return 'show'
}

export function getReportRoute({
  restoreOutcome,
  hasCurrentExam,
  hasSession,
  sessionMode,
  isSubmitted,
  hasResult,
}: ResultPageRouteInput) {
  if (restoreOutcome === 'restoring') {
    return 'loading'
  }

  if (restoreOutcome === 'missing') {
    return 'toHome'
  }

  if (!hasCurrentExam || !hasSession) {
    return 'loading'
  }

  if (sessionMode !== 'real') {
    return 'toHome'
  }

  if (!isSubmitted) {
    return 'toExam'
  }

  if (!hasResult) {
    return 'toHome'
  }

  return 'show'
}
