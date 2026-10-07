import { readFile } from "fs/promises";
import path from "path";
import { NextResponse } from "next/server";
import { generatedQuestionDir } from "@/lib/generated-files";
import type { GeneratedQuestion } from "@/lib/types";

function isGeneratedQuestion(value: unknown): value is GeneratedQuestion {
  if (!value || typeof value !== "object") return false;
  const question = value as Partial<GeneratedQuestion>;
  return (
    typeof question.id === "string" &&
    typeof question.stem_text === "string" &&
    Array.isArray(question.choices) &&
    Array.isArray(question.shared_asset_refs) &&
    Array.isArray(question.assets)
  );
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ examId: string; questionId: string }> },
) {
  const { examId, questionId } = await context.params;
  const dir = generatedQuestionDir(examId, questionId);
  if (!dir) {
    return NextResponse.json(null, {
      headers: { "Cache-Control": "no-store" },
    });
  }

  try {
    const raw = await readFile(path.join(dir, "question.json"), "utf-8");
    const parsed: unknown = JSON.parse(raw);
    if (!isGeneratedQuestion(parsed)) {
      return NextResponse.json(null, {
        headers: { "Cache-Control": "no-store" },
      });
    }
    return NextResponse.json(parsed, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(null, {
      headers: { "Cache-Control": "no-store" },
    });
  }
}
