import { describe, expect, it } from 'vitest'
import {
  calculateExamResult,
  createExamSession,
  getPracticeResumeSummary,
  getCanSubmit,
  getLiveQuestionStatuses,
  getSessionRemainingSeconds,
  hasMeaningfulPracticeProgress,
  migrateExamSessionQuestionKeys,
  REAL_EXAM_DURATION_SECONDS,
} from './examSession'
import type { Exam } from '../types/exam'
import type { ExamSession } from '../types/examSession'

const examFixture: Exam = {
  paper_id: 'Exam_Fixture',
  questions: [
    {
      id: 1,
      stem_text: 'Question 1',
      options: {
        A: { text: 'A' },
        B: { text: 'B' },
      },
      answer: 'A',
      points: 3,
    },
    {
      id: 2,
      stem_text: 'Question 2',
      options: {
        A: { text: 'A' },
        B: { text: 'B' },
      },
      answer: 'B',
      points: 4,
    },
    {
      id: 3,
      stem_text: 'Question 3',
      options: {
        A: { text: 'A' },
        B: { text: 'B' },
      },
      answer: 'B',
      points: 5,
    },
  ],
}

const practiceExamFixture: Exam = {
  paper_id: 'Practice_Bank',
  questions: [
    {
      id: 1,
      practiceQuestionId: 101,
      sourceRef: {
        examId: 'Exam_2020',
        questionId: 1,
        questionNumber: 1,
      },
      stem_text: 'Practice Question 1',
      options: {
        A: { text: 'A' },
        B: { text: 'B' },
      },
      answer: 'A',
      points: 3,
    },
    {
      id: 2,
      practiceQuestionId: 202,
      sourceRef: {
        examId: 'Exam_2020',
        questionId: 2,
        questionNumber: 2,
      },
      stem_text: 'Practice Question 2',
      options: {
        A: { text: 'A' },
        B: { text: 'B' },
      },
      answer: 'B',
      points: 4,
    },
    {
      id: 1,
      practiceQuestionId: 303,
      sourceRef: {
        examId: 'Exam_2021',
        questionId: 1,
        questionNumber: 1,
      },
      stem_text: 'Practice Question 3',
      options: {
        A: { text: 'A' },
        B: { text: 'B' },
      },
      answer: 'B',
      points: 5,
    },
  ],
}

function createSubmittedSession(overrides: Partial<ExamSession>): ExamSession {
  return {
    ...createExamSession('Exam_Fixture', 'real', 0),
    submittedAt: REAL_EXAM_DURATION_SECONDS * 1000,
    submitReason: 'manual',
    ...overrides,
  }
}

describe('examSession helpers', () => {
  it('calculates official real exam scores with base points and penalties', () => {
    const session = createSubmittedSession({
      mode: 'real',
      answers: {
        1: 'A',
        2: 'A',
      },
    })

    const result = calculateExamResult(examFixture, session, REAL_EXAM_DURATION_SECONDS * 1000)

    expect(result).not.toBeNull()
    expect(result?.score).toBe(20)
    expect(result?.scoreLabel).toBe('20/90')
    expect(result?.correctCount).toBe(1)
    expect(result?.incorrectCount).toBe(1)
    expect(result?.unansweredCount).toBe(1)
    expect(result?.questionResults.map((question) => question.scoreDelta)).toEqual([3, -1, 0])
  })

  it('calculates practice scores without penalties', () => {
    const session = createSubmittedSession({
      mode: 'practice',
      submitReason: 'practice_finish',
      answers: {
        1: 'A',
        2: 'A',
      },
    })

    const result = calculateExamResult(examFixture, session, 120_000)

    expect(result).not.toBeNull()
    expect(result?.score).toBe(3)
    expect(result?.scoreLabel).toBe('3/12')
    expect(result?.questionResults.map((question) => question.scoreDelta)).toEqual([3, 0, 0])
  })

  it('tracks remaining time from timestamps for real exams', () => {
    const session = createExamSession('Exam_Fixture', 'real', 1_000)

    expect(getSessionRemainingSeconds(session, 1_000)).toBe(REAL_EXAM_DURATION_SECONDS)
    expect(getSessionRemainingSeconds(session, 61_000)).toBe(REAL_EXAM_DURATION_SECONDS - 60)
    expect(getSessionRemainingSeconds(session, 9_999_999_999)).toBe(0)
  })

  it('treats blank practice sessions as not resumable', () => {
    expect(hasMeaningfulPracticeProgress(createExamSession('Exam_Fixture', 'practice', 0))).toBe(false)
  })

  it('treats navigated or drafted practice sessions as resumable', () => {
    const navigatedSession = createExamSession('Exam_Fixture', 'practice', 0)
    navigatedSession.currentQuestionIndex = 1

    const draftedSession = createExamSession('Exam_Fixture', 'practice', 0)
    draftedSession.answers = {
      1: 'A',
    }

    expect(hasMeaningfulPracticeProgress(navigatedSession)).toBe(true)
    expect(hasMeaningfulPracticeProgress(draftedSession)).toBe(true)
  })

  it('does not resume finished practice sessions and derives a compact summary for active ones', () => {
    const activeSession = createExamSession('Exam_Fixture', 'practice', 0)
    activeSession.currentQuestionIndex = 2
    activeSession.answers = {
      1: 'A',
      2: 'B',
    }
    activeSession.submittedQuestionIds = [1]

    const finishedSession = createExamSession('Exam_Fixture', 'practice', 0)
    finishedSession.answers = {
      1: 'A',
    }
    finishedSession.submittedAt = 1_000
    finishedSession.submitReason = 'practice_finish'

    expect(getPracticeResumeSummary(activeSession)).toEqual({
      checkedCount: 1,
      answeredCount: 2,
      currentQuestionIndex: 2,
      currentQuestionNumber: 3,
    })
    expect(hasMeaningfulPracticeProgress(finishedSession)).toBe(false)
    expect(getPracticeResumeSummary(finishedSession)).toBeNull()
  })

  it('derives live question statuses for a real exam using answered state plus active selection', () => {
    const session = createExamSession('Exam_Fixture', 'real', 0)
    session.currentQuestionIndex = 0
    session.answers = {
      3: 'B',
    }

    const statuses = getLiveQuestionStatuses(examFixture, session)

    expect(statuses.map((status) => status.tone)).toEqual(['unanswered', 'unanswered', 'answered'])
    expect(statuses.map((status) => status.isSelected)).toEqual([true, false, false])
  })

  it('derives live question statuses for practice using correct and incorrect submissions', () => {
    const session = createExamSession('Practice_Bank', 'practice', 0)
    session.currentQuestionIndex = 1
    session.answers = {
      101: 'A',
      202: 'A',
    }
    session.submittedQuestionIds = [101, 202]

    const statuses = getLiveQuestionStatuses(practiceExamFixture, session)

    expect(statuses.map((status) => status.tone)).toEqual(['correct', 'incorrect', 'unanswered'])
    expect(statuses.map((status) => status.isSelected)).toEqual([false, true, false])
    expect(statuses.map((status) => status.questionId)).toEqual([101, 202, 303])
  })

  it('only enables manual submit after every question has an answer', () => {
    const incompleteSession = createExamSession('Exam_Fixture', 'real', 0)
    incompleteSession.answers = {
      1: 'A',
      2: 'B',
    }

    const completeSession = createExamSession('Exam_Fixture', 'real', 0)
    completeSession.answers = {
      1: 'A',
      2: 'B',
      3: 'B',
    }

    expect(getCanSubmit(examFixture, incompleteSession)).toBe(false)
    expect(getCanSubmit(examFixture, completeSession)).toBe(true)
    expect(getCanSubmit(examFixture, createExamSession('Exam_Fixture', 'practice', 0))).toBe(false)
  })

  it('migrates legacy practice sessions onto explicit practice question ids', () => {
    const legacySession: ExamSession = {
      ...createExamSession('Practice_Bank', 'practice', 0),
      questionKeyVersion: 1,
      answers: {
        1: 'A',
        2: 'B',
        3: 'A',
      },
      submittedQuestionIds: [2, 3],
    }

    const migratedSession = migrateExamSessionQuestionKeys(practiceExamFixture, legacySession)

    expect(migratedSession.questionKeyVersion).toBe(2)
    expect(migratedSession.answers).toEqual({
      101: 'A',
      202: 'B',
      303: 'A',
    })
    expect(migratedSession.submittedQuestionIds).toEqual([202, 303])
  })
})
