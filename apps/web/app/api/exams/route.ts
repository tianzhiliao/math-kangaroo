import { readFile } from "fs/promises";
import { join } from "path";
import { NextResponse } from "next/server";
import { getReleaseDataRoot } from "@/lib/paths";

export async function GET() {
  try {
    const manifestPath = join(getReleaseDataRoot(), "manifest.json");
    const raw = await readFile(manifestPath, "utf-8");
    return NextResponse.json(JSON.parse(raw));
  } catch {
    return NextResponse.json(
      { error: "manifest_not_found", message: "Could not read release-data/manifest.json" },
      { status: 500 },
    );
  }
}
