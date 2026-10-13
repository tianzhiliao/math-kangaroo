"use client";

import { FeedbackPill } from "@/components/exam/FeedbackPill";
import { Button } from "@/components/ui/Button";
import { generatedAssetUrl } from "@/lib/asset-url";
import { useGeneratedExplanation } from "@/lib/queries";
import { useSimilarAnswersStore } from "@/lib/similar-answers-store";
import type { GeneratedQuestion } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ExplanationBody } from "./ExplanationBody";
import { QuestionCard } from "./QuestionCard";

async function fetchSimilarQuestion(
  examId: string,
  questionId: string,
): Promise<GeneratedQuestion | null> {
  const response = await fetch(
    `/api/generated/${encodeURIComponent(examId)}/${encodeURIComponent(questionId)}`,
  );
  if (!response.ok) return null;
  const body: unknown = await response.json();
  if (!body || typeof body !== "object") return null;
  return body as GeneratedQuestion;
}

/**
 * An AI-generated question with the same idea as the one above, answered in
 * place: pick a choice, see right or wrong, read why, answer again. Answers
 * are kept per source question and never touch the practice score.
 */
export function GeneratedQuestionSection({
  examId,
  questionId,
  questionNumber,
}: {
  examId: string;
  questionId: string;
  /** Number of the source question; read-aloud looks the variant up by it. */
  questionNumber: number;
}) {
  const { data } = useQuery({
    queryKey: ["generated-question", examId, questionId],
    queryFn: () => fetchSimilarQuestion(examId, questionId),
    staleTime: Infinity,
    retry: false,
  });

  const questionKey = `${examId}/${questionId}`;
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [whyKey, setWhyKey] = useState<string | null>(null);
  const open = openKey === questionKey;
  const showWhy = whyKey === questionKey;

  const selected = useSimilarAnswersStore((s) => s.answers[questionKey] ?? null);
  const setAnswer = useSimilarAnswersStore((s) => s.setAnswer);
  const reset = useSimilarAnswersStore((s) => s.reset);

  const explanationQuery = useGeneratedExplanation(examId, questionId, open);

  if (!data) return null;

  // An explanation written for a different key would teach the wrong answer.
  const explanation =
    explanationQuery.data && explanationQuery.data.answer === data.answer
      ? explanationQuery.data
      : null;

  // A variant shared with an identical question in another paper carries that
  // paper's number; read-aloud needs this paper's.
  const question = { ...data, number: questionNumber };

  const labels = data.choices.map((c) => c.label);
  // A stored answer from an older version of this question no longer applies.
  const answered = selected !== null && labels.includes(selected);
  const isCorrect = answered && selected === data.answer;
  const correctText = data.choices.find((c) => c.label === data.answer)?.text;

  const status = !answered
    ? "Same idea, new numbers and pictures"
    : isCorrect
      ? "You got this one right"
      : "Not quite yet. Answer it again?";

  return (
    <section
      aria-label="Similar question"
      className="w-full rounded-panel bg-mk-series-level-p px-5 py-5 md:px-6"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-meta text-mk-ink-60">Practice more</p>
          <h2 className="mt-0.5 text-h5">Try a similar question</h2>
          <p className="mt-0.5 text-meta text-mk-ink-60">{status}</p>
        </div>
        <Button
          variant={open ? "outline" : "primary"}
          aria-expanded={open}
          onClick={() => setOpenKey(open ? null : questionKey)}
          className={open ? "border-transparent" : ""}
        >
          {open ? "Hide" : answered ? "Show" : "Try it"}
        </Button>
      </div>
      {open ? (
        <div className="mk-fade-in mt-4 rounded-card bg-mk-bg p-[18px]">
          <QuestionCard
            examId={examId}
            question={question}
            allAssets={data.assets}
            selectedLabel={answered ? selected : null}
            onSelect={(label) => {
              if (!answered) setAnswer(questionKey, label);
            }}
            disabled={answered}
            showOutcome={answered}
            correctLabel={data.answer}
            compact
            variant
            metaLabel="Similar question · does not count toward your score"
            outcomeNote={
              answered ? (
                <div className="flex flex-wrap items-center gap-3">
                  <FeedbackPill
                    isCorrect={isCorrect}
                    correctLabel={data.answer}
                    correctText={correctText}
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setWhyKey(null);
                      reset(questionKey);
                    }}
                  >
                    Answer again
                  </Button>
                </div>
              ) : null
            }
            resolveAssetUrl={(asset) =>
              generatedAssetUrl(examId, questionId, asset.path)
            }
          />
          {answered && explanation ? (
            showWhy ? (
              <div className="mk-fade-in mt-5">
                <ExplanationBody explanation={explanation} selectedLabel={selected} />
              </div>
            ) : (
              <div className="mt-4">
                <Button variant="secondary" onClick={() => setWhyKey(questionKey)}>
                  Show explanation
                </Button>
              </div>
            )
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
