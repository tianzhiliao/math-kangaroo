import { PageChrome } from "@/components/page-chrome";
import { PracticeLibrary } from "@/components/practice-library";
import { getCatalog } from "@/lib/data";

export default async function PracticeLibraryPage() {
  const catalog = await getCatalog();

  return (
    <PageChrome
      kicker="Practice mode"
      title="Practice across the whole archive."
      note="Filter the bank, jump to any question, and get immediate correctness feedback without leaving the one-question focus."
      active="practice"
    >
      <PracticeLibrary exams={catalog.exams} questionIndex={catalog.questionIndex} />
    </PageChrome>
  );
}
