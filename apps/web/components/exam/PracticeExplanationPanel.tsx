"use client";

import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { isAiEnabledOnClient } from "@/lib/ai-features";
import {
  getFriendlyAiErrorMessage,
  readApiError,
} from "@/lib/api-errors";
import type { AIExplanationRequest, AIExplanationResponse } from "@/lib/types";
import { useEffect, useState } from "react";

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
  const aiEnabled = isAiEnabledOnClient();
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

  if (!aiEnabled || !selectedLabel) {
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

  return (
    <section className="mt-3 rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wide text-amber-900/75">
            Explanation
          </p>
          <p className="mt-1 text-sm font-semibold text-amber-950">
            Get a short answer in simple English.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="tap-target inline-flex min-h-[44px] items-center justify-center rounded-xl bg-amber-600 px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-amber-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2"
        >
          {open ? "Hide explanation" : "Show explanation"}
        </button>
      </div>

      {open ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-white/90 p-4">
          <div className="mb-3 flex justify-end">
            <button
              type="button"
              onClick={() => void handleRegenerate()}
              disabled={isRegenerating || isLoading}
              className="tap-target inline-flex min-h-[36px] items-center justify-center rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-bold text-amber-900 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isRegenerating ? "Regenerating..." : "Regenerate explanation"}
            </button>
          </div>
          {isLoading ? (
            <div className="flex items-center gap-3 text-slate-700">
              <span
                className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent"
                aria-hidden
              />
              <span className="text-sm font-medium">
                Writing the explanation...
              </span>
            </div>
          ) : hasError ? (
            <div className="space-y-3">
              <p className="text-sm font-medium text-rose-700">
                {errorMessage}
              </p>
              <button
                type="button"
                onClick={() => void explanationQuery.refetch()}
                className="tap-target inline-flex min-h-[40px] items-center justify-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2"
              >
                Try again
              </button>
            </div>
          ) : explanation ? (
            <div className="space-y-3">
              <div className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-950">
                Correct answer: {explanation.correct_label}
                {explanation.cache_hit ? (
                  <span className="ml-2 text-[11px] font-bold uppercase tracking-wide text-amber-700">
                    Cached
                  </span>
                ) : null}
              </div>
              <p className="text-base leading-relaxed text-slate-900">
                {explanation.explanation}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-700">
              Tap the button to get the explanation.
            </p>
          )}
        </div>
      ) : null}
    </section>
  );
}
