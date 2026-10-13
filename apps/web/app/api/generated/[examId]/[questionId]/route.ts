import { readFile } from "fs/promises";
import path from "path";
import { NextResponse } from "next/server";
import {
  isGeneratedQuestion,
  resolveGeneratedQuestionDir,
} from "@/lib/generated-files";

const NO_STORE = { headers: { "Cache-Control": "no-store" } };

export async function GET(
  _request: Request,
  context: { params: Promise<{ examId: string; questionId: string }> },
) {
  const { examId, questionId } = await context.params;
  const dir = await resolveGeneratedQuestionDir(examId, questionId);
  if (!dir) return NextResponse.json(null, NO_STORE);

  try {
    const raw = await readFile(path.join(dir, "question.json"), "utf-8");
    const parsed: unknown = JSON.parse(raw);
    if (!isGeneratedQuestion(parsed)) return NextResponse.json(null, NO_STORE);
    return NextResponse.json(parsed, NO_STORE);
  } catch {
    return NextResponse.json(null, NO_STORE);
  }
}
