import { PracticeSessionLoader } from "@/components/exam/SessionLoader";

export default async function PracticeByIdPage({
  params,
}: {
  params: Promise<{ examId: string }>;
}) {
  const { examId } = await params;
  return <PracticeSessionLoader examId={examId} />;
}
