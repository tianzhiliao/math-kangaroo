import { readFile } from "fs/promises";
import { join } from "path";
import { NextResponse } from "next/server";
import { getReleaseDataRoot } from "@/lib/paths";
import type { Exam, Manifest, PracticeBankEntry } from "@/lib/types";

/**
 * Flatten all questions from all exams in manifest order into one bank (1..N).
 */
export async function GET() {
  try {
    const root = getReleaseDataRoot();
    const manifestRaw = await readFile(join(root, "manifest.json"), "utf-8");
    const manifest = JSON.parse(manifestRaw) as Manifest;
    const entries: PracticeBankEntry[] = [];

    for (const e of manifest.exams) {
      const examPath = join(root, e.path);
      const examRaw = await readFile(examPath, "utf-8");
      const exam = JSON.parse(examRaw) as Exam;
      for (const q of exam.questions) {
        const correct = exam.answer_key[String(q.number)] ?? "";
        entries.push({
          exam_id: e.exam_id,
          question_number: q.number,
          correct_label: correct,
        });
      }
    }

    return NextResponse.json({
      total: entries.length,
      entries,
    });
  } catch {
    return NextResponse.json(
      { error: "practice_bank_failed" },
      { status: 500 },
    );
  }
}
