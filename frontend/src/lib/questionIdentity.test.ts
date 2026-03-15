import { describe, expect, it } from 'vitest'
import {
  getQuestionAudioTarget,
  getQuestionSessionId,
  getQuestionSourceLabel,
} from './questionIdentity'
import type { Question } from '../types/exam'

describe('questionIdentity helpers', () => {
  it('keeps real exam audio targets on the paper question id', () => {
    const question: Question = {
      id: 4,
      stem_text: 'Real question',
      options: {
        A: { text: 'A' },
      },
      answer: 'A',
      points: 3,
    }

    expect(getQuestionSessionId(question)).toBe(4)
    expect(getQuestionAudioTarget(question, 'Exam_2020', 4)).toEqual({
      playbackKey: 'Exam_2020:4',
      examId: 'Exam_2020',
      questionId: 4,
    })
  })

  it('routes practice audio through the source ref while keeping a separate session id', () => {
    const question: Question = {
      id: 32,
      practiceQuestionId: 58,
      sourceRef: {
        examId: 'Exam_2021',
        questionId: 14,
        questionNumber: 14,
      },
      stem_text: 'Practice question',
      options: {
        A: { text: 'A' },
      },
      answer: 'A',
      points: 4,
    }

    expect(getQuestionSessionId(question)).toBe(58)
    expect(getQuestionAudioTarget(question, 'Practice_Bank')).toEqual({
      playbackKey: 'Practice_Bank:58',
      examId: 'Exam_2021',
      questionId: 14,
    })
    expect(getQuestionSourceLabel(question)).toBe('Exam 2021 · Q14')
  })
})
