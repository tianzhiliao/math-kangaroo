"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { PageState } from "@/components/ui/PageState";
import { usePracticeAnswersStore } from "@/lib/practice-answers-store";
import { usePracticeBank } from "@/lib/queries";

export default function PracticeIndexPage() {
  const router = useRouter();
  const lastVisitedQuestion = usePracticeAnswersStore(
    (s) => s.lastVisitedQuestion,
  );
  const { data: bank, isPending } = usePracticeBank();
  const total = bank?.total ?? 0;
  const targetQuestion =
    typeof lastVisitedQuestion === "number" &&
    lastVisitedQuestion >= 1 &&
    lastVisitedQuestion <= total
      ? lastVisitedQuestion
      : 1;

  useEffect(() => {
    if (isPending || total < 1) return;
    router.replace(`/practice/q/${targetQuestion}`);
  }, [isPending, router, targetQuestion, total]);

  if (isPending) {
    return <PageState message="Loading question bank…" />;
  }

  if (!bank?.total) {
    return (
      <PageState
        title="No questions yet"
        message="They appear here once added."
        actions={
          <ButtonLink href="/" variant="secondary">
            Back to home
          </ButtonLink>
        }
      />
    );
  }

  return <PageState message="Opening practice…" />;
}
