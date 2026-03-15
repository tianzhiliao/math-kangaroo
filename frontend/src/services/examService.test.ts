import { describe, expect, it } from 'vitest'
import { buildPracticeExam, PRACTICE_EXAM_ID } from './examService'
import type { Exam } from '../types/exam'

const examFixtures: Exam[] = [
  {
    paper_id: 'Exam_2020',
    questions: [
      {
        id: 1,
        stem_text: '2020 Q1',
        options: {
          A: { text: 'A' },
          B: { text: 'B' },
        },
        answer: 'A',
        points: 3,
      },
      {
        id: 2,
        stem_text: '2020 Q2',
        options: {
          A: { text: 'A' },
          B: { text: 'B' },
        },
        answer: 'B',
        points: 4,
      },
    ],
  },
  {
    paper_id: 'Exam_2021',
    questions: [
      {
        id: 1,
        stem_text: '2021 Q1',
        options: {
          A: { text: 'A' },
          B: { text: 'B' },
        },
        answer: 'A',
        points: 3,
      },
    ],
  },
]

describe('buildPracticeExam', () => {
  it('flattens all exams into one ordered practice bank with source metadata', () => {
    const practiceExam = buildPracticeExam(examFixtures)

    expect(practiceExam.paper_id).toBe(PRACTICE_EXAM_ID)
    expect(practiceExam.questions.map((question) => question.id)).toEqual([1, 2, 1])
    expect(practiceExam.questions.map((question) => question.practiceQuestionId)).toEqual([1, 2, 3])
    expect(practiceExam.questions.map((question) => question.sourceRef?.examId)).toEqual([
      'Exam_2020',
      'Exam_2020',
      'Exam_2021',
    ])
    expect(practiceExam.questions.map((question) => question.sourceRef?.questionId)).toEqual([1, 2, 1])
    expect(practiceExam.questions.map((question) => question.sourceRef?.questionNumber)).toEqual([1, 2, 1])
  })
})
