import { cache } from "react";
import path from "node:path";
import { promises as fs } from "node:fs";

import type { CatalogData, HydratedExam, NormalizedExam } from "@/lib/types";

const dataRoot = path.join(process.cwd(), "data");

async function readJsonFile<T>(filePath: string): Promise<T> {
  const content = await fs.readFile(filePath, "utf8");
  return JSON.parse(content) as T;
}

export const getCatalog = cache(async (): Promise<CatalogData> => {
  return readJsonFile<CatalogData>(path.join(dataRoot, "catalog.json"));
});

export const getExamById = cache(async (examId: string): Promise<HydratedExam> => {
  const exam = await readJsonFile<NormalizedExam>(path.join(dataRoot, "exams", `${examId}.json`));

  return {
    ...exam,
    questionLookup: Object.fromEntries(exam.questions.map((question) => [question.number, question])),
  };
});

export async function getAllExamIds() {
  const catalog = await getCatalog();
  return catalog.exams.map((exam) => exam.examId);
}

export async function getAllPracticeParams() {
  const catalog = await getCatalog();
  return catalog.questionIndex.map((entry) => ({
    examId: entry.examId,
    questionNumber: String(entry.questionNumber),
  }));
}
