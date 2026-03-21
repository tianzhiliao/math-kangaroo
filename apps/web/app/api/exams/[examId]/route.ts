import { readFile } from "fs/promises";
import { join } from "path";
import { NextResponse } from "next/server";
import { getReleaseDataRoot } from "@/lib/paths";

export async function GET(
  _request: Request,
  context: { params: Promise<{ examId: string }> },
) {
  const { examId } = await context.params;
  try {
    const examPath = join(
      getReleaseDataRoot(),
      "exams",
      examId,
      "exam.json",
    );
    const raw = await readFile(examPath, "utf-8");
    return NextResponse.json(JSON.parse(raw));
  } catch {
    return NextResponse.json({ error: "exam_not_found" }, { status: 404 });
  }
}
