export interface Graphic {
  id: string;
  svg_path: string;
}

export interface QuestionOption {
  text: string;
  graphics?: Graphic[];
}

export interface QuestionSourceRef {
  examId: string;
  questionId: number;
  questionNumber: number;
}

export interface Question {
  id: number;
  stem_text: string;
  stem_graphics?: Graphic[];
  options: Record<string, QuestionOption>;
  answer: string;
  points: number;
  score_group?: string;
  sourceSchema?: string;
  practiceQuestionId?: number;
  sourceRef?: QuestionSourceRef;
}

export interface Exam {
  paper_id: string;
  questions: Question[];
}
