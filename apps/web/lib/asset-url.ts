/**
 * Public URL for a file under the exam directory (e.g. assets/q01_stem_01.png).
 */
export function rawExamFileUrl(examId: string, relativePath: string): string {
  const segments = relativePath.split("/").filter(Boolean);
  return `/api/exams/${encodeURIComponent(examId)}/raw/${segments.map(encodeURIComponent).join("/")}`;
}

/** Public URL for an SVG under a generated similar-question folder. */
export function generatedAssetUrl(
  examId: string,
  questionId: string,
  relativePath: string,
): string {
  const segments = relativePath.split("/").filter(Boolean);
  return `/api/generated/${encodeURIComponent(examId)}/${encodeURIComponent(questionId)}/raw/${segments.map(encodeURIComponent).join("/")}`;
}
