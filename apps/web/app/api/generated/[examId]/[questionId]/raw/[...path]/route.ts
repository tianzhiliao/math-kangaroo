import { readFile } from "fs/promises";
import { NextResponse } from "next/server";
import { generatedAssetFile } from "@/lib/generated-files";

export async function GET(
  _request: Request,
  context: {
    params: Promise<{ examId: string; questionId: string; path: string[] }>;
  },
) {
  const { examId, questionId, path: segments } = await context.params;
  const file = generatedAssetFile(examId, questionId, segments ?? []);
  if (!file) {
    return new NextResponse("Not found", { status: 404 });
  }

  try {
    const buf = await readFile(file);
    return new NextResponse(buf, {
      headers: {
        "Content-Type": "image/svg+xml",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return new NextResponse("Not found", { status: 404 });
  }
}
