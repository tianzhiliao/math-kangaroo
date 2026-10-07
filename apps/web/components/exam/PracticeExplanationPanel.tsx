"use client";

import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import {
  getFriendlyAiErrorMessage,
  readApiError,
} from "@/lib/api-errors";
import type { AIExplanationRequest, AIExplanationResponse } from "@/lib/types";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { RefreshIcon, Spinner } from "@/components/ui/icons";

export function PracticeExplanationPanel({
  examId,
  questionNumber,
  selectedLabel,
  expectedCorrectLabel,
}: {
  examId: string;
  questionNumber: number;
  selectedLabel: string | null;
  expectedCorrectLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regenerateError, setRegenerateError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const queryKey = ["ai-explanation", examId, questionNumber, selectedLabel] as const;

  useEffect(() => {
    setOpen(false);
    setRegenerateError(null);
  }, [examId, questionNumber, selectedLabel]);

  const explanationQuery = useQuery({
    queryKey,
    queryFn: async () => {
      const payload: AIExplanationRequest = {
        exam_id: examId,
        question_number: questionNumber,
        selected_label: selectedLabel ?? "",
      };
      const response = await fetch("/api/ai/explanation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw await readApiError(
          response,
          `Explanation request failed (${response.status})`,
        );
      }

      return response.json() as Promise<AIExplanationResponse>;
    },
    enabled: open && Boolean(selectedLabel),
    staleTime: Infinity,
    gcTime: 1000 * 60 * 60 * 24,
    retry: 1,
  });

  const handleRegenerate = async () => {
    if (!selectedLabel || isRegenerating) return;
    setIsRegenerating(true);
    setRegenerateError(null);
    try {
      const payload: AIExplanationRequest = {
        exam_id: examId,
        question_number: questionNumber,
        selected_label: selectedLabel,
        force_refresh: true,
      };
      const response = await fetch("/api/ai/explanation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw await readApiError(
          response,
          `Explanation request failed (${response.status})`,
        );
      }
      const fresh = (await response.json()) as AIExplanationResponse;
      queryClient.setQueryData(queryKey, fresh);
      setOpen(true);
    } catch (error) {
      setRegenerateError(
        getFriendlyAiErrorMessage(
          error,
          "Sorry, we could not regenerate the explanation.",
        ),
      );
    } finally {
      setIsRegenerating(false);
    }
  };

  if (!selectedLabel) {
    return null;
  }

  const isLoading = open && explanationQuery.isFetching && !explanationQuery.data;
  const explanation = explanationQuery.data;
  const actualCorrectLabel = explanation?.correct_label ?? "";
  const hasMismatch =
    Boolean(actualCorrectLabel) &&
    Boolean(expectedCorrectLabel) &&
    actualCorrectLabel !== expectedCorrectLabel;
  const hasError =
    open && (explanationQuery.isError || hasMismatch || Boolean(regenerateError));
  const errorMessage = regenerateError
    ? regenerateError
    : hasMismatch
    ? "The explanation response did not match this question's answer key. Please try again."
    : getFriendlyAiErrorMessage(
        explanationQuery.error,
        "Sorry, we could not load the explanation.",
      );

  const header = (meta: React.ReactNode, title: React.ReactNode) => (
    <div className="min-w-0">
      <p className="text-meta text-mk-ink-60">{meta}</p>
      <h2 className="mt-0.5 text-h4">{title}</h2>
    </div>
  );

  const hideButton = (
    <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
      Hide
    </Button>
  );

  if (!open) {
    return (
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-panel border border-mk-ink-12 px-6 py-5 md:px-7">
        <div className="min-w-0">
          <h2 className="text-h5">Want to know why?</h2>
          <p className="mt-0.5 text-meta text-mk-ink-60">
            A short explanation in simple English
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>Show explanation</Button>
      </section>
    );
  }

  if (isLoading || (!explanation && !hasError)) {
    return (
      <section
        className="rounded-panel border border-mk-ink-12 px-6 py-6 md:px-7"
        aria-busy="true"
      >
        <p className="text-meta text-mk-ink-60" role="status">
          Writing the explanation…
        </p>
        <div className="mt-4 flex flex-col gap-3" aria-hidden>
          <span className="h-3 w-[80%] rounded-full bg-mk-ink-4" />
          <span className="h-3 w-[62%] rounded-full bg-mk-ink-4" />
        </div>
      </section>
    );
  }

  if (hasError) {
    return (
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-panel bg-mk-wrong-subtle px-6 py-5 md:px-7">
        <p className="min-w-0 flex-1 text-[16px] leading-6 text-mk-wrong-fg" role="alert">
          {errorMessage}
        </p>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => {
              setRegenerateError(null);
              void explanationQuery.refetch();
            }}
          >
            Try again
          </Button>
          {hideButton}
        </div>
      </section>
    );
  }

  if (!explanation) {
    return null;
  }

  const paragraphs = splitParagraphs(explanation.explanation);

  return (
    <section className="mk-fade-in rounded-panel border border-mk-ink-12 px-6 py-6 md:px-7">
      <div className="flex items-start justify-between gap-4">
        {header(
          <>
            Explanation · checked against the answer key
            {explanation.cache_hit ? " · Saved" : ""}
          </>,
          `Why the answer is ${explanation.correct_label}`,
        )}
        <div className="flex shrink-0 items-center gap-2">
          <IconButton
            aria-label="Write the explanation again"
            title="Write the explanation again"
            aria-busy={isRegenerating}
            disabled={isRegenerating}
            onClick={() => void handleRegenerate()}
            className="disabled:cursor-wait"
          >
            {isRegenerating ? <Spinner /> : <RefreshIcon />}
          </IconButton>
          {hideButton}
        </div>
      </div>
      <div className="mt-4 flex max-w-[60ch] flex-col gap-3 text-explain-m md:text-explain">
        {paragraphs.map((text, i) => (
          <p key={i}>{text}</p>
        ))}
      </div>
    </section>
  );
}

/** Newlines first; a single block is split into one sentence per paragraph. */
function splitParagraphs(text: string): string[] {
  const blocks = text
    .split(/\n+/)
    .map((b) => b.trim())
    .filter(Boolean);
  if (blocks.length > 1) return blocks;
  return (blocks[0] ?? "")
    .split(/(?<=[.!?])\s+(?=[A-Z0-9])/)
    .map((b) => b.trim())
    .filter(Boolean);
}
