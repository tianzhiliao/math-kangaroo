"use client";

import { useQuery } from "@tanstack/react-query";
import type {
  Exam,
  ExplanationsResponse,
  Manifest,
  PracticeBankResponse,
  QuestionExplanation,
} from "./types";

export function useManifest() {
  return useQuery({
    queryKey: ["manifest"],
    queryFn: async () => {
      const r = await fetch("/api/exams");
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<Manifest>;
    },
  });
}

export function usePracticeBank() {
  return useQuery({
    queryKey: ["practice-bank"],
    queryFn: async () => {
      const r = await fetch("/api/practice-bank");
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<PracticeBankResponse>;
    },
  });
}

export function useExam(examId: string | undefined) {
  return useQuery({
    queryKey: ["exam", examId],
    queryFn: async () => {
      const r = await fetch(`/api/exams/${encodeURIComponent(examId!)}`);
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<Exam>;
    },
    enabled: !!examId,
  });
}

/** Pre-generated explanations for an exam's original questions. */
export function useExamExplanations(examId: string, enabled = true) {
  return useQuery({
    queryKey: ["explanations", examId],
    queryFn: async () => {
      const r = await fetch(`/api/exams/${encodeURIComponent(examId)}/explanations`);
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<ExplanationsResponse>;
    },
    enabled,
    staleTime: Infinity,
  });
}

/** Pre-generated explanation for one similar question, or null when none is shown. */
export function useGeneratedExplanation(examId: string, questionId: string, enabled = true) {
  return useQuery({
    queryKey: ["generated-explanation", examId, questionId],
    queryFn: async () => {
      const r = await fetch(
        `/api/generated/${encodeURIComponent(examId)}/${encodeURIComponent(questionId)}/explanation`,
      );
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<QuestionExplanation | null>;
    },
    enabled,
    staleTime: Infinity,
  });
}
