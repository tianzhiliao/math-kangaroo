import path from "path";
import { getGeneratedQuestionsRoot } from "@/lib/paths";

const EXAM_ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const QUESTION_ID_PATTERN = /^q\d{2}$/;
const SVG_FILE_PATTERN = /^[a-z0-9][a-z0-9._-]*\.svg$/;

export function generatedQuestionDir(
  examId: string,
  questionId: string,
): string | null {
  if (!EXAM_ID_PATTERN.test(examId) || !QUESTION_ID_PATTERN.test(questionId)) {
    return null;
  }
  const root = path.resolve(getGeneratedQuestionsRoot());
  const dir = path.resolve(root, examId, questionId);
  if (dir !== path.join(root, examId, questionId)) return null;
  return dir;
}

/** Resolve a single SVG inside a generated question folder. */
export function generatedAssetFile(
  examId: string,
  questionId: string,
  segments: string[],
): string | null {
  if (segments.length !== 1) return null;
  const name = segments[0];
  if (!SVG_FILE_PATTERN.test(name)) return null;
  if (name === "compare.png" || name === "card.png") return null;
  const dir = generatedQuestionDir(examId, questionId);
  if (!dir) return null;
  const file = path.resolve(dir, name);
  if (file !== path.join(dir, name)) return null;
  return file;
}
