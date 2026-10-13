import { readFile } from "fs/promises";
import path from "path";
import { NextResponse } from "next/server";
import { toPublicExplanation } from "@/lib/explanations";
import { generatedQuestionDir } from "@/lib/generated-files";

export async function GET(
  _request: Request,
  context: { params: Promise<{ examId: string; questionId: string }> },
) {
  const { examId, questionId } = await context.params;
  const dir = generatedQuestionDir(examId, questionId);
  let explanation = null;
  if (dir) {
    try {
      const raw = await readFile(path.join(dir, "explanation.json"), "utf-8");
      explanation = toPublicExplanation(JSON.parse(raw));
    } catch {
      explanation = null;
    }
  }
  return NextResponse.json(explanation, {
    headers: { "Cache-Control": "no-store" },
  });
}
