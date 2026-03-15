import type { Exam, Graphic, Question, QuestionOption, QuestionSourceRef } from '../types/exam';

export const EXAM_IDS = ['Exam_2020', 'Exam_2021', 'Exam_2022', 'Exam_2023'] as const;
export const PRACTICE_EXAM_ID = 'Practice_Bank';

function resolveGraphics(
  graphics: Graphic[] | undefined,
  baseUrl: string,
): Graphic[] | undefined {
  if (!graphics) {
    return graphics;
  }

  return graphics.map((graphic) => ({
    ...graphic,
    svg_path: new URL(graphic.svg_path, baseUrl).toString(),
  }));
}

function resolveOptions(
  options: Record<string, QuestionOption>,
  baseUrl: string,
): Record<string, QuestionOption> {
  return Object.fromEntries(
    Object.entries(options).map(([key, option]) => [
      key,
      {
        ...option,
        graphics: resolveGraphics(option.graphics, baseUrl),
      },
    ]),
  );
}

function resolveExamAssetPaths(exam: Exam, baseUrl: string): Exam {
  return {
    ...exam,
    questions: exam.questions.map((question: Question) => ({
      ...question,
      stem_graphics: resolveGraphics(question.stem_graphics, baseUrl),
      options: resolveOptions(question.options, baseUrl),
    })),
  };
}

async function fetchExam(examId: string): Promise<Exam> {
  const response = await fetch(`/data/${examId}.json`);
  if (!response.ok) {
    throw new Error(`Failed to load exam ${examId}`);
  }
  const data = await response.json() as Exam;
  return resolveExamAssetPaths(data, response.url);
}

function buildQuestionSourceRef(
  examId: string,
  question: Question,
  questionIndex: number,
): QuestionSourceRef {
  return {
    examId,
    questionId: question.id,
    questionNumber: questionIndex + 1,
  };
}

export function buildPracticeExam(exams: Exam[]): Exam {
  let practiceQuestionId = 1;

  return {
    paper_id: PRACTICE_EXAM_ID,
    questions: exams.flatMap((exam) =>
      exam.questions.map((question, questionIndex) => ({
        ...question,
        practiceQuestionId: practiceQuestionId++,
        sourceRef: buildQuestionSourceRef(exam.paper_id, question, questionIndex),
      })),
    ),
  };
}

export async function getExam(examId: string): Promise<Exam> {
  if (examId === PRACTICE_EXAM_ID) {
    const exams = await Promise.all(EXAM_IDS.map((id) => fetchExam(id)));
    return buildPracticeExam(exams);
  }

  return fetchExam(examId);
}

export async function getAllExams(): Promise<string[]> {
  return [...EXAM_IDS];
}
