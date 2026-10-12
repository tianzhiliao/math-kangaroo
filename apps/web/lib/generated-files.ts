import { readFile, stat } from "fs/promises";
import path from "path";
import { getGeneratedQuestionsRoot } from "@/lib/paths";
import type { GeneratedQuestion } from "@/lib/types";

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

async function isFile(file: string): Promise<boolean> {
  try {
    return (await stat(file)).isFile();
  } catch {
    return false;
  }
}

interface ManifestEntry {
  id?: unknown;
  status?: unknown;
  duplicate_of?: unknown;
  duplicate_question?: unknown;
}

/**
 * Folder holding the similar question for a source question. A question the
 * generator skipped as a duplicate of one in another paper reuses that
 * paper's variant (manifest `duplicate_of` + `duplicate_question`).
 */
export async function resolveGeneratedQuestionDir(
  examId: string,
  questionId: string,
): Promise<string | null> {
  const dir = generatedQuestionDir(examId, questionId);
  if (!dir) return null;
  if (await isFile(path.join(dir, "question.json"))) return dir;

  try {
    const manifestPath = path.join(path.dirname(dir), "manifest.json");
    const manifest = JSON.parse(await readFile(manifestPath, "utf-8")) as {
      questions?: ManifestEntry[];
    };
    const entry = manifest.questions?.find((q) => q.id === questionId);
    if (
      entry?.status !== "skipped-duplicate" ||
      typeof entry.duplicate_of !== "string" ||
      typeof entry.duplicate_question !== "string"
    ) {
      return null;
    }
    const target = generatedQuestionDir(
      entry.duplicate_of,
      entry.duplicate_question,
    );
    if (target && (await isFile(path.join(target, "question.json")))) {
      return target;
    }
  } catch {
    // No manifest, or an unreadable one: there is no variant.
  }
  return null;
}

/** Resolve a single SVG inside a generated question folder. */
export async function generatedAssetFile(
  examId: string,
  questionId: string,
  segments: string[],
): Promise<string | null> {
  if (segments.length !== 1) return null;
  const name = segments[0];
  if (!SVG_FILE_PATTERN.test(name)) return null;
  const dir = await resolveGeneratedQuestionDir(examId, questionId);
  if (!dir) return null;
  const file = path.resolve(dir, name);
  if (file !== path.join(dir, name)) return null;
  return file;
}

/**
 * Shape check for question.json. A variant the app cannot run (no choices,
 * an answer that is not a choice, a figure ref with no asset) is treated as
 * missing rather than shown broken.
 */
export function isGeneratedQuestion(value: unknown): value is GeneratedQuestion {
  if (!value || typeof value !== "object") return false;
  const q = value as Partial<GeneratedQuestion>;
  if (
    typeof q.id !== "string" ||
    typeof q.number !== "number" ||
    typeof q.stem_text !== "string" ||
    typeof q.answer !== "string" ||
    !Array.isArray(q.choices) ||
    !Array.isArray(q.shared_asset_refs) ||
    !Array.isArray(q.assets)
  ) {
    return false;
  }
  const assetIds = new Set(
    q.assets
      .filter((a) => a && typeof a.id === "string" && typeof a.path === "string")
      .map((a) => a.id),
  );
  const labels = new Set<string>();
  for (const choice of q.choices) {
    if (
      !choice ||
      typeof choice.label !== "string" ||
      typeof choice.text !== "string" ||
      !Array.isArray(choice.asset_refs) ||
      labels.has(choice.label) ||
      choice.asset_refs.some((ref) => !assetIds.has(ref))
    ) {
      return false;
    }
    labels.add(choice.label);
  }
  return (
    labels.size >= 2 &&
    labels.has(q.answer) &&
    q.shared_asset_refs.every((ref) => assetIds.has(ref))
  );
}
