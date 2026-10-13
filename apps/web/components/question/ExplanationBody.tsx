import type { QuestionExplanation } from "@/lib/types";

/** Key idea, numbered steps and the answer line; adds a note for a wrong pick. */
export function ExplanationBody({
  explanation,
  selectedLabel,
}: {
  explanation: QuestionExplanation;
  selectedLabel: string | null;
}) {
  const pickedFeedback =
    selectedLabel && selectedLabel !== explanation.answer
      ? explanation.choice_feedback[selectedLabel]
      : undefined;

  return (
    <div className="flex max-w-[60ch] flex-col gap-4 text-explain-m md:text-explain">
      {pickedFeedback ? (
        <p className="rounded-card bg-mk-wrong-subtle px-4 py-3 text-mk-wrong-fg">
          <span className="font-semibold">You picked {selectedLabel}. </span>
          {pickedFeedback}
        </p>
      ) : null}
      <p className="font-semibold">{explanation.key_idea}</p>
      <ol className="flex flex-col gap-3">
        {explanation.steps.map((step, i) => (
          <li key={i} className="flex gap-3">
            <span
              aria-hidden
              className="mt-[3px] flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-mk-ink-4 text-meta font-semibold text-mk-ink-80"
            >
              {i + 1}
            </span>
            <span className="min-w-0">{step}</span>
          </li>
        ))}
      </ol>
      <p className="rounded-card bg-mk-right-surface px-4 py-3 font-semibold text-mk-right-fg">
        {explanation.answer_sentence}
      </p>
    </div>
  );
}
