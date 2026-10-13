"use client";

import { useEffect, useState } from "react";
import { ExplanationBody } from "@/components/question/ExplanationBody";
import { Button } from "@/components/ui/Button";
import { useExamExplanations } from "@/lib/queries";

export function PracticeExplanationPanel({
  examId,
  questionId,
  selectedLabel,
  expectedCorrectLabel,
}: {
  examId: string;
  questionId: string;
  selectedLabel: string | null;
  expectedCorrectLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const { data } = useExamExplanations(examId);

  useEffect(() => {
    setOpen(false);
  }, [examId, questionId, selectedLabel]);

  const explanation = data?.questions[questionId];
  // An explanation written for a different key would teach the wrong answer; hide it.
  if (!selectedLabel || !explanation || explanation.answer !== expectedCorrectLabel) {
    return null;
  }

  if (!open) {
    return (
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-panel border border-mk-ink-12 px-6 py-5 md:px-7">
        <div className="min-w-0">
          <h2 className="text-h5">Want to know why?</h2>
          <p className="mt-0.5 text-meta text-mk-ink-60">
            A step-by-step explanation in simple English
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>Show explanation</Button>
      </section>
    );
  }

  return (
    <section className="mk-fade-in rounded-panel border border-mk-ink-12 px-6 py-6 md:px-7">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-meta text-mk-ink-60">Explanation</p>
          <h2 className="mt-0.5 text-h4">Why the answer is {explanation.answer}</h2>
        </div>
        <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
          Hide
        </Button>
      </div>
      <div className="mt-4">
        <ExplanationBody explanation={explanation} selectedLabel={selectedLabel} />
      </div>
    </section>
  );
}
