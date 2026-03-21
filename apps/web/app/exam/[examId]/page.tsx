import { ExamSessionLoader } from "@/components/exam/SessionLoader";

export default async function ExamByIdPage({
  params,
}: {
  params: Promise<{ examId: string }>;
}) {
  const { examId } = await params;
  return <ExamSessionLoader examId={examId} />;
}
