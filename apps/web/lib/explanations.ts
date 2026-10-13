import { readFile } from "fs/promises";
import path from "path";
import { getReleaseDataRoot } from "@/lib/paths";
import type { QuestionExplanation } from "@/lib/types";

const EXAM_ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SHOWN_STATUSES = new Set(["unreviewed", "approved"]);

/**
 * Keep only what a child should see. Flagged entries (broken figure, disputed
 * key, method-only steps) stay hidden until a person approves them, and review
 * notes, hashes and the blind solver's answer never leave the server.
 */
export function toPublicExplanation(entry: unknown): QuestionExplanation | null {
  if (!entry || typeof entry !== "object") return null;
  const e = entry as Record<string, unknown>;
  const review = e.review as { status?: unknown } | undefined;
  if (!review || !SHOWN_STATUSES.has(String(review.status))) return null;
  if (
    typeof e.answer !== "string" ||
    typeof e.key_idea !== "string" ||
    typeof e.answer_sentence !== "string" ||
    !Array.isArray(e.steps) ||
    !e.steps.every((step) => typeof step === "string") ||
    !e.choice_feedback ||
    typeof e.choice_feedback !== "object"
  ) {
    return null;
  }
  return {
    answer: e.answer,
    key_idea: e.key_idea,
    steps: e.steps as string[],
    answer_sentence: e.answer_sentence,
    choice_feedback: e.choice_feedback as Record<string, string>,
  };
}

/** Explanations for an exam's original questions, keyed by question id. */
export async function loadOriginalExplanations(
  examId: string,
): Promise<Record<string, QuestionExplanation>> {
  if (!EXAM_ID_PATTERN.test(examId)) return {};
  const file = path.join(getReleaseDataRoot(), "exams", examId, "explanations.json");
  let parsed: unknown;
  try {
    parsed = JSON.parse(await readFile(file, "utf-8"));
  } catch {
    return {};
  }
  const questions = (parsed as { questions?: unknown })?.questions;
  if (!questions || typeof questions !== "object") return {};
  const result: Record<string, QuestionExplanation> = {};
  for (const [questionId, entry] of Object.entries(questions)) {
    const explanation = toPublicExplanation(entry);
    if (explanation) result[questionId] = explanation;
  }
  return result;
}
