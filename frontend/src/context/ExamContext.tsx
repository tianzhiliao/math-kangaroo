/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { FC, ReactNode } from 'react'
import { getExam } from '../services/examService'
import {
  REAL_EXAM_DURATION_SECONDS,
  calculateExamResult,
  coerceExamSession,
  createExamSession,
  getPracticeResumeSummary,
  getAnsweredCount,
  getCanSubmit,
  getExamSessionStorageKey,
  getLiveQuestionStatuses,
  migrateExamSessionQuestionKeys,
  getSessionRemainingSeconds,
  getSubmittedCount,
  hasMeaningfulPracticeProgress,
} from '../lib/examSession'
import { getQuestionSessionId } from '../lib/questionIdentity'
import type { Exam } from '../types/exam'
import type {
  ExamMode,
  ExamResult,
  ExamSession,
  PracticeResumeSummary,
  QuestionStatus,
  SubmitReason,
} from '../types/examSession'
import { PRACTICE_EXAM_ID } from '../services/examService'

interface ExamContextType {
  currentExam: Exam | null
  session: ExamSession | null
  currentMode: ExamMode | null
  currentQuestionIndex: number
  answers: Record<number, string>
  submittedQuestions: number[]
  remainingSeconds: number | null
  answeredCount: number
  submittedCount: number
  canSubmit: boolean
  isPracticeComplete: boolean
  isSubmitted: boolean
  submitReason: SubmitReason | null
  result: ExamResult | null
  questionStatuses: QuestionStatus[]
  isLoading: boolean
  error: string | null
  getSavedPracticeResumeSummary: () => PracticeResumeSummary | null
  startExam: (examId: string, mode: ExamMode) => Promise<boolean>
  resumeExam: (examId: string, mode: ExamMode, allowCreate?: boolean) => Promise<boolean>
  selectAnswer: (questionId: number, answer: string) => void
  submitQuestion: (questionId: number) => void
  nextQuestion: () => void
  prevQuestion: () => void
  jumpToQuestion: (index: number) => void
  submitExam: (reason?: SubmitReason) => void
  resetExam: (examId?: string, mode?: ExamMode) => void
}

const ExamContext = createContext<ExamContextType | undefined>(undefined)

export const useExam = () => {
  const context = useContext(ExamContext)
  if (!context) {
    throw new Error('useExam must be used within an ExamProvider')
  }
  return context
}

interface ExamProviderProps {
  children: ReactNode
}

function clampSessionToExam(session: ExamSession, exam: Exam) {
  const migratedSession = migrateExamSessionQuestionKeys(exam, session)
  const questionIds = new Set(exam.questions.map((question) => getQuestionSessionId(question)))
  const answers = Object.fromEntries(
    Object.entries(migratedSession.answers).filter(([questionId]) =>
      questionIds.has(Number(questionId)),
    ),
  )
  const submittedQuestionIds = migratedSession.submittedQuestionIds.filter((questionId) =>
    questionIds.has(questionId),
  )

  return {
    ...migratedSession,
    currentQuestionIndex: Math.min(
      Math.max(migratedSession.currentQuestionIndex, 0),
      Math.max(exam.questions.length - 1, 0),
    ),
    answers,
    submittedQuestionIds,
  }
}

export const ExamProvider: FC<ExamProviderProps> = ({ children }) => {
  const [currentExam, setCurrentExam] = useState<Exam | null>(null)
  const [session, setSession] = useState<ExamSession | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [now, setNow] = useState(() => Date.now())

  const persistSession = useCallback((nextSession: ExamSession | null) => {
    if (!nextSession) {
      return
    }

    window.localStorage.setItem(
      getExamSessionStorageKey(nextSession.examId, nextSession.mode),
      JSON.stringify(nextSession),
    )
  }, [])

  const removePersistedSession = useCallback((examId: string, mode: ExamMode) => {
    window.localStorage.removeItem(getExamSessionStorageKey(examId, mode))
  }, [])

  const readPersistedSession = useCallback((examId: string, mode: ExamMode) => {
    try {
      const storedValue = window.localStorage.getItem(getExamSessionStorageKey(examId, mode))
      if (!storedValue) {
        return null
      }

      return coerceExamSession(JSON.parse(storedValue), examId, mode)
    } catch (storageError) {
      console.error(storageError)
      return null
    }
  }, [])

  const loadExamSession = useCallback(
    async (examId: string, mode: ExamMode, allowCreate: boolean) => {
      setIsLoading(true)
      setError(null)

      try {
        const exam = await getExam(examId)
        const storedSession = readPersistedSession(examId, mode)
        const nextSession = storedSession
          ? clampSessionToExam(storedSession, exam)
          : allowCreate
            ? createExamSession(examId, mode)
            : null

        setCurrentExam(exam)
        setSession(nextSession)

        if (nextSession) {
          persistSession(nextSession)
        }

        return nextSession !== null
      } catch (loadError) {
        console.error(loadError)
        setCurrentExam(null)
        setSession(null)
        setError('Failed to load exam data')
        return false
      } finally {
        setIsLoading(false)
      }
    },
    [persistSession, readPersistedSession],
  )

  const updateSession = useCallback(
    (updater: (previousSession: ExamSession) => ExamSession) => {
      setSession((previousSession) => {
        if (!previousSession) {
          return previousSession
        }

        const nextSession = updater(previousSession)
        persistSession(nextSession)
        return nextSession
      })
    },
    [persistSession],
  )

  useEffect(() => {
    if (!session || session.submittedAt !== null) {
      return
    }

    const syncClock = () => {
      setNow(Date.now())
    }

    syncClock()
    const interval = window.setInterval(syncClock, 1000)
    return () => {
      window.clearInterval(interval)
    }
  }, [session])

  const currentMode = session?.mode ?? null
  const currentQuestionIndex = session?.currentQuestionIndex ?? 0
  const answers = session?.answers ?? {}
  const submittedQuestions = session?.submittedQuestionIds ?? []
  const remainingSeconds = session ? getSessionRemainingSeconds(session, now) : null
  const answeredCount = session ? getAnsweredCount(session) : 0
  const submittedCount = session ? getSubmittedCount(session) : 0
  const canSubmit = currentExam && session ? getCanSubmit(currentExam, session) : false
  const isPracticeComplete =
    currentExam !== null &&
    session !== null &&
    session.mode === 'practice' &&
    submittedCount === currentExam.questions.length
  const isSubmitted = Boolean(session?.submittedAt)
  const submitReason = session?.submitReason ?? null

  const questionStatuses = useMemo(() => {
    if (!currentExam || !session) {
      return []
    }

    return getLiveQuestionStatuses(currentExam, session)
  }, [currentExam, session])

  const result = useMemo<ExamResult | null>(() => {
    if (!currentExam || !session || session.submitReason === null) {
      return null
    }

    return calculateExamResult(currentExam, session, now)
  }, [currentExam, now, session])

  const getSavedPracticeResumeSummary = useCallback(() => {
    if (
      session?.examId === PRACTICE_EXAM_ID &&
      session.mode === 'practice' &&
      hasMeaningfulPracticeProgress(session)
    ) {
      return getPracticeResumeSummary(session)
    }

    return getPracticeResumeSummary(readPersistedSession(PRACTICE_EXAM_ID, 'practice'))
  }, [readPersistedSession, session])

  const startExam = useCallback(
    async (examId: string, mode: ExamMode) => {
      setIsLoading(true)
      setError(null)

      try {
        const exam = await getExam(examId)
        const freshSession = createExamSession(examId, mode)

        setCurrentExam(exam)
        setSession(freshSession)
        persistSession(freshSession)
        return true
      } catch (loadError) {
        console.error(loadError)
        setCurrentExam(null)
        setSession(null)
        setError('Failed to load exam data')
        return false
      } finally {
        setIsLoading(false)
      }
    },
    [persistSession],
  )

  const resumeExam = useCallback(
    async (examId: string, mode: ExamMode, allowCreate = true) => {
      if (currentExam?.paper_id === examId && session?.examId === examId && session.mode === mode) {
        return true
      }

      return loadExamSession(examId, mode, allowCreate)
    },
    [currentExam?.paper_id, loadExamSession, session],
  )

  const selectAnswer = useCallback(
    (questionId: number, answer: string) => {
      updateSession((previousSession) => {
        if (previousSession.submittedAt !== null) {
          return previousSession
        }

        if (
          previousSession.mode === 'practice' &&
          previousSession.submittedQuestionIds.includes(questionId)
        ) {
          return previousSession
        }

        return {
          ...previousSession,
          answers: {
            ...previousSession.answers,
            [questionId]: answer,
          },
        }
      })
    },
    [updateSession],
  )

  const submitQuestion = useCallback(
    (questionId: number) => {
      updateSession((previousSession) => {
        if (
          previousSession.mode !== 'practice' ||
          previousSession.submittedAt !== null ||
          previousSession.answers[questionId] === undefined ||
          previousSession.submittedQuestionIds.includes(questionId)
        ) {
          return previousSession
        }

        return {
          ...previousSession,
          submittedQuestionIds: [...previousSession.submittedQuestionIds, questionId],
        }
      })
    },
    [updateSession],
  )

  const nextQuestion = useCallback(() => {
    updateSession((previousSession) => {
      const questionCount = currentExam?.questions.length ?? 0
      if (questionCount === 0) {
        return previousSession
      }

      return {
        ...previousSession,
        currentQuestionIndex: Math.min(previousSession.currentQuestionIndex + 1, questionCount - 1),
      }
    })
  }, [currentExam?.questions.length, updateSession])

  const prevQuestion = useCallback(() => {
    updateSession((previousSession) => ({
      ...previousSession,
      currentQuestionIndex: Math.max(previousSession.currentQuestionIndex - 1, 0),
    }))
  }, [updateSession])

  const jumpToQuestion = useCallback(
    (index: number) => {
      updateSession((previousSession) => {
        const questionCount = currentExam?.questions.length ?? 0
        if (questionCount === 0) {
          return previousSession
        }

        return {
          ...previousSession,
          currentQuestionIndex: Math.min(Math.max(index, 0), questionCount - 1),
        }
      })
    },
    [currentExam?.questions.length, updateSession],
  )

  const submitExam = useCallback(
    (reason: SubmitReason = 'manual') => {
      updateSession((previousSession) => {
        if (previousSession.submittedAt !== null) {
          return previousSession
        }

        const submittedAt =
          reason === 'timeout' && previousSession.mode === 'real'
            ? previousSession.startedAt + REAL_EXAM_DURATION_SECONDS * 1000
            : Date.now()

        return {
          ...previousSession,
          submittedAt,
          submitReason: reason,
        }
      })
    },
    [updateSession],
  )

  const resetExam = useCallback(
    (examId?: string, mode?: ExamMode) => {
      const targetExamId = examId ?? session?.examId
      const targetMode = mode ?? session?.mode

      if (targetExamId && targetMode) {
        removePersistedSession(targetExamId, targetMode)
      }

      if (!targetExamId || !targetMode) {
        setCurrentExam(null)
        setSession(null)
        setError(null)
        return
      }

      if (!session || (session.examId === targetExamId && session.mode === targetMode)) {
        setCurrentExam(null)
        setSession(null)
        setError(null)
      }
    },
    [removePersistedSession, session],
  )

  useEffect(() => {
    if (session?.mode !== 'real' || session.submittedAt !== null) {
      return
    }

    if (remainingSeconds === 0) {
      submitExam('timeout')
    }
  }, [remainingSeconds, session, submitExam])

  return (
    <ExamContext.Provider
      value={{
        currentExam,
        session,
        currentMode,
        currentQuestionIndex,
        answers,
        submittedQuestions,
        remainingSeconds,
        answeredCount,
        submittedCount,
        canSubmit,
        isPracticeComplete,
        isSubmitted,
        submitReason,
        result,
        questionStatuses,
        isLoading,
        error,
        getSavedPracticeResumeSummary,
        startExam,
        resumeExam,
        selectAnswer,
        submitQuestion,
        nextQuestion,
        prevQuestion,
        jumpToQuestion,
        submitExam,
        resetExam,
      }}
    >
      {children}
    </ExamContext.Provider>
  )
}
