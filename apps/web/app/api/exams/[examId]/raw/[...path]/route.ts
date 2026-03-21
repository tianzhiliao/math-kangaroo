import { readFile } from "fs/promises";
import path from "path";
import { NextResponse } from "next/server";
import { getReleaseDataRoot } from "@/lib/paths";

function contentTypeForPath(relPath: string): string {
  if (relPath.endsWith(".png")) return "image/png";
  if (relPath.endsWith(".json")) return "application/json";
  return "application/octet-stream";
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ examId: string; path: string[] }> },
) {
  const { examId, path: segments } = await context.params;
  if (!segments?.length) {
    return new NextResponse("Not found", { status: 404 });
  }

  const base = path.resolve(getReleaseDataRoot(), "exams", examId);
  const resolved = path.resolve(base, ...segments);
  if (!resolved.startsWith(base)) {
    return new NextResponse("Forbidden", { status: 403 });
  }

  try {
    const buf = await readFile(resolved);
    return new NextResponse(buf, {
      headers: {
        "Content-Type": contentTypeForPath(resolved),
        "Cache-Control": "public, max-age=31536000, immutable",
      },
    });
  } catch {
    return new NextResponse("Not found", { status: 404 });
  }
}
