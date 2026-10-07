import path from "path";

/**
 * Resolve `release-data` directory. Override with RELEASE_DATA_PATH in Docker/production.
 */
export function getReleaseDataRoot(): string {
  if (process.env.RELEASE_DATA_PATH) {
    return path.resolve(process.env.RELEASE_DATA_PATH);
  }
  // apps/web -> repo root/release-data
  return path.resolve(process.cwd(), "..", "..", "release-data");
}

/**
 * Root of generated similar questions, one folder per source question.
 * Override with GENERATED_QUESTIONS_PATH. Default is the repo's generated/ directory.
 */
export function getGeneratedQuestionsRoot(): string {
  if (process.env.GENERATED_QUESTIONS_PATH) {
    return path.resolve(process.env.GENERATED_QUESTIONS_PATH);
  }
  // apps/web -> repo root/generated
  return path.resolve(process.cwd(), "..", "..", "generated");
}
