import { ExamLibrary } from "@/components/exam-library";
import { PageChrome } from "@/components/page-chrome";
import { getCatalog } from "@/lib/data";

export default async function ExamLibraryPage() {
  const catalog = await getCatalog();

  return (
    <PageChrome
      kicker="Mock exam mode"
      title="Rehearse the full paper."
      note="Pick an official paper, choose where to begin, then run it like the real thing with timing, scoring, and submission."
      active="exam"
    >
      <ExamLibrary exams={catalog.exams} />
    </PageChrome>
  );
}
