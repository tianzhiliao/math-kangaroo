import { notFound } from "next/navigation";

import { PageChrome } from "@/components/page-chrome";
import { PracticeExperience } from "@/components/practice-experience";
import { getAllPracticeParams, getCatalog, getExamById } from "@/lib/data";

export async function generateStaticParams() {
  return getAllPracticeParams();
}

export default async function PracticeQuestionPage({
  params,
}: {
  params: Promise<{ examId: string; questionNumber: string }>;
}) {
  const { examId, questionNumber } = await params;
  const numericQuestionNumber = Number(questionNumber);

  if (!Number.isFinite(numericQuestionNumber)) {
    notFound();
  }

  try {
    const [exam, catalog] = await Promise.all([getExamById(examId), getCatalog()]);

    if (!exam.questionLookup[numericQuestionNumber]) {
      notFound();
    }

    return (
      <PageChrome
        kicker="Practice mode"
        title={`${exam.title} · Question ${numericQuestionNumber}`}
        note="One question on the screen, instant correctness feedback after submission, and free movement across your current practice pool."
        active="practice"
      >
        <PracticeExperience exam={exam} questionNumber={numericQuestionNumber} allQuestions={catalog.questionIndex} />
      </PageChrome>
    );
  } catch {
    notFound();
  }
}
