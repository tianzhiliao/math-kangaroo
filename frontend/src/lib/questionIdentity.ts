import type { Exam, Question, QuestionSourceRef } from '../types/exam'

export interface QuestionAudioTarget {
  playbackKey: string
  examId: string
  questionId: number
}

export function getExamDisplayLabel(examId: string) {
  return examId.replace(/_/g, ' ')
}

export function getQuestionSessionId(question: Question) {
  return question.practiceQuestionId ?? question.id
}

export function getQuestionSourceRef(
  question: Question,
  fallbackExamId: string,
  fallbackQuestionNumber?: number,
): QuestionSourceRef {
  if (question.sourceRef) {
    return question.sourceRef
  }

  return {
    examId: fallbackExamId,
    questionId: question.id,
    questionNumber: fallbackQuestionNumber ?? question.id,
  }
}

export function getQuestionAudioTarget(
  question: Question,
  fallbackExamId: string,
  fallbackQuestionNumber?: number,
): QuestionAudioTarget {
  const sourceRef = getQuestionSourceRef(question, fallbackExamId, fallbackQuestionNumber)

  return {
    playbackKey: `${fallbackExamId}:${getQuestionSessionId(question)}`,
    examId: sourceRef.examId,
    questionId: sourceRef.questionId,
  }
}

export function getQuestionSourceLabel(question: Question) {
  if (!question.sourceRef) {
    return null
  }

  return `${getExamDisplayLabel(question.sourceRef.examId)} · Q${question.sourceRef.questionNumber}`
}

export function getLegacyPracticeQuestionIdMap(exam: Exam) {
  const legacyQuestionIds = new Map<number, number>()

  exam.questions.forEach((question, questionIndex) => {
    legacyQuestionIds.set(questionIndex + 1, getQuestionSessionId(question))
  })

  return legacyQuestionIds
}
