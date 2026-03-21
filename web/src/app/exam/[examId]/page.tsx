import { notFound } from "next/navigation";

import { ExamExperience } from "@/components/exam-experience";
import { PageChrome } from "@/components/page-chrome";
import { getAllExamIds, getExamById } from "@/lib/data";

export async function generateStaticParams() {
  const examIds = await getAllExamIds();
  return examIds.map((examId) => ({ examId }));
}

export default async function ExamPage({
  params,
}: {
  params: Promise<{ examId: string }>;
}) {
  const { examId } = await params;

  try {
    const exam = await getExamById(examId);

    return (
      <PageChrome
        kicker="Mock exam mode"
        title={exam.title}
        note="Timed, scored, and fully navigable. Your progress is saved locally in this browser until you finish or restart."
        active="exam"
      >
        <ExamExperience exam={exam} />
      </PageChrome>
    );
  } catch {
    notFound();
  }
}
