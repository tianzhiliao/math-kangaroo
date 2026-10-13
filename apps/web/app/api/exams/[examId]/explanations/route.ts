import { NextResponse } from "next/server";
import { loadOriginalExplanations } from "@/lib/explanations";
import type { ExplanationsResponse } from "@/lib/types";

export async function GET(
  _request: Request,
  context: { params: Promise<{ examId: string }> },
) {
  const { examId } = await context.params;
  const body: ExplanationsResponse = {
    questions: await loadOriginalExplanations(examId),
  };
  return NextResponse.json(body, { headers: { "Cache-Control": "no-store" } });
}
