"use client";

import { Button, ButtonLink } from "@/components/ui/Button";
import { PageState } from "@/components/ui/PageState";
import { useExam } from "@/lib/queries";
import { ExamRun } from "./ExamRun";
import { PracticeRun } from "./PracticeRun";

function Fail({ onRetry }: { onRetry: () => void }) {
  return (
    <PageState
      title="Could not load this exam"
      message="Check the connection and try again."
      actions={
        <>
          <Button onClick={onRetry}>Try again</Button>
          <ButtonLink href="/" variant="secondary">
            Back to home
          </ButtonLink>
        </>
      }
    />
  );
}

export function ExamSessionLoader({ examId }: { examId: string }) {
  const { data, isPending, error, refetch } = useExam(examId);
  if (isPending) return <PageState message="Loading paper…" />;
  if (error || !data) return <Fail onRetry={() => void refetch()} />;
  return <ExamRun exam={data} />;
}

export function PracticeSessionLoader({ examId }: { examId: string }) {
  const { data, isPending, error, refetch } = useExam(examId);
  if (isPending) return <PageState message="Loading paper…" />;
  if (error || !data) return <Fail onRetry={() => void refetch()} />;
  return <PracticeRun exam={data} />;
}
